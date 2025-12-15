"""
Template-Based OCR Document Alignment - Phase 1: Global Feature-Based Registration

Complete implementation using OpenCV for robust document alignment

PHASE 1 implements:
  1.1 Feature Detection and Matching (SIFT/ORB)
  1.2 Homography Computation (RANSAC)
  1.3 Image Warping and Registration

RESEARCH SUMMARY (2025):
  - SIFT: Most accurate (~65% match rate even with 45° rotation), but slower
  - ORB: 14x faster than SURF, 24x faster than SIFT, free/license-free, 
         performs comparably for most applications
  - For document alignment: ORB recommended for speed, SIFT for maximum accuracy
  - RANSAC: Robust to outliers, handles 4+ point correspondences
  - OpenCV 4.5+: SIFT is patent-free and available

LIBRARIES:
  - opencv-python (4.5.0+): Image processing and feature detection
  - numpy: Numerical operations
  - dataclasses: Type hints and configuration management

USAGE EXAMPLE:
  from phase_1_alignment import FeatureBasedAligner, AlignmentConfig
  
  config = AlignmentConfig(feature_detector="ORB", verbose=True)
  aligner = FeatureBasedAligner(config)
  result = aligner.align(input_image, template_image)
  
  aligned_image = result.aligned_image
  homography = result.homography_matrix
  inlier_ratio = result.inlier_ratio  # Should be > 40%
  error = result.reprojection_error    # Should be < 5px
"""

import cv2
import numpy as np
from dataclasses import dataclass
from typing import Tuple, Optional, List


@dataclass
class AlignmentConfig:
    """Configuration for image alignment process"""
    feature_detector: str = "ORB"  # "ORB" or "SIFT"
    max_features: int = 5000
    ratio_test_threshold: float = 0.7  # Lowe's ratio test threshold
    ransac_threshold: float = 5.0  # RANSAC reprojection threshold in pixels
    min_matches: int = 10  # Minimum required matches for homography
    verbose: bool = True


@dataclass
class AlignmentResult:
    """Result of image alignment containing output and metrics"""
    aligned_image: np.ndarray
    homography_matrix: np.ndarray
    inlier_mask: np.ndarray
    good_matches: List
    keypoints_template: List
    keypoints_input: List
    inlier_ratio: float  # Percentage of inliers
    reprojection_error: float  # Mean pixel distance
    num_inliers: int


class FeatureBasedAligner:
    """
    Phase 1: Global Feature-Based Registration
    
    Aligns input document image to template using:
    - Feature detection and matching (SIFT or ORB)
    - Homography computation via RANSAC
    - Perspective warping with bilinear interpolation
    
    QUALITY THRESHOLDS:
    - Inlier ratio: > 40% (percentage of matched features that are inliers)
    - Reprojection error: < 5 pixels (mean distance after transformation)
    - Minimum matches: >= 10 (required for stable homography)
    """
    
    def __init__(self, config: AlignmentConfig = None):
        """Initialize aligner with configuration"""
        self.config = config or AlignmentConfig()
        self._init_detector()
        
    def _init_detector(self):
        """Initialize feature detector based on configuration"""
        detector_name = self.config.feature_detector.upper()
        
        if detector_name == "SIFT":
            self.detector = cv2.SIFT_create()
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
            self.norm_type = cv2.NORM_L2
            if self.config.verbose:
                print("[INFO] Using SIFT detector (Scale-Invariant Feature Transform)")
                print("       Pros: Highest accuracy, rotation/scale invariant")
                print("       Cons: Slower (~1-3 seconds per image)")
        else:  # ORB (default)
            self.detector = cv2.ORB_create(
                nfeatures=self.config.max_features,
                scaleFactor=1.2,
                nlevels=8
            )
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
            self.norm_type = cv2.NORM_HAMMING
            if self.config.verbose:
                print("[INFO] Using ORB detector (Oriented FAST and Rotated BRIEF)")
                print("       Pros: 24x faster than SIFT, free license, efficient")
                print("       Cons: Less robust to extreme rotations (>45°)")
    
    def detect_features(self, image: np.ndarray) -> Tuple[List, Optional[np.ndarray]]:
        """
        Detect keypoints and compute descriptors
        
        Uses FAST corner detection (ORB) or DoG (SIFT) to identify
        interest points, then computes local descriptors.
        
        Args:
            image: Input image (BGR or grayscale)
            
        Returns:
            (keypoints, descriptors) tuple
        """
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
            
        keypoints, descriptors = self.detector.detectAndCompute(gray, None)
        
        if self.config.verbose:
            print(f"[INFO] Detected {len(keypoints)} keypoints")
            
        return keypoints, descriptors
    
    def match_features(
        self,
        descriptors_input: np.ndarray,
        descriptors_template: np.ndarray
    ) -> List:
        """
        Match features between input and template using Lowe's ratio test
        
        LOWE'S RATIO TEST:
        For each feature in input image, find its 2 nearest neighbors in template.
        Accept match only if distance to nearest < 0.7 * distance to 2nd nearest.
        This filters out ambiguous matches.
        
        Args:
            descriptors_input: Descriptors from input image (N x D)
            descriptors_template: Descriptors from template image (M x D)
            
        Returns:
            List of DMatch objects representing good matches
        """
        # KNN matching: k=2 to get two best matches for ratio test
        matches = self.matcher.knnMatch(descriptors_input, descriptors_template, k=2)
        
        # Apply Lowe's ratio test to filter weak matches
        good_matches = []
        for match_pair in matches:
            if len(match_pair) == 2:
                m, n = match_pair
                # Distance ratio test: best match must be significantly better
                if m.distance < self.config.ratio_test_threshold * n.distance:
                    good_matches.append(m)
        
        if self.config.verbose:
            ratio = (len(good_matches) / len(matches) * 100) if matches else 0
            print(f"[INFO] Found {len(good_matches)}/{len(matches)} good matches ({ratio:.1f}%)")
            
        return good_matches
    
    def compute_homography(
        self,
        keypoints_input: List,
        keypoints_template: List,
        good_matches: List
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray], int]:
        """
        Compute homography using RANSAC (Random Sample Consensus)
        
        RANSAC ALGORITHM:
        1. Randomly sample 4 point correspondences
        2. Compute homography from these 4 points
        3. Count inliers (points where reprojection error < threshold)
        4. Repeat and keep homography with most inliers
        5. Return final homography refined using all inliers
        
        PARAMETERS:
        - Minimum samples: 4 points (homography has 8 DOF)
        - Inlier threshold: 5.0 pixels (RANSAC reprojection)
        - Iterations: ~500 (default for OpenCV)
        
        Args:
            keypoints_input: Keypoints from input image
            keypoints_template: Keypoints from template image
            good_matches: Matched keypoint pairs (DMatch objects)
            
        Returns:
            (homography_matrix: 3x3, inlier_mask: Nx1, num_inliers: int)
        """
        # Check minimum matches requirement
        if len(good_matches) < self.config.min_matches:
            if self.config.verbose:
                print(f"[WARNING] Insufficient matches: {len(good_matches)} < {self.config.min_matches}")
            return None, None, 0
        
        # Extract point coordinates from matched features
        src_pts = np.float32([
            keypoints_input[m.queryIdx].pt for m in good_matches
        ]).reshape(-1, 1, 2)  # Query index = input image
        
        dst_pts = np.float32([
            keypoints_template[m.trainIdx].pt for m in good_matches
        ]).reshape(-1, 1, 2)  # Train index = template image
        
        # Compute homography with RANSAC
        homography_matrix, mask = cv2.findHomography(
            src_pts, dst_pts,
            method=cv2.RANSAC,
            ransacReprojThreshold=self.config.ransac_threshold
        )
        
        if homography_matrix is None:
            if self.config.verbose:
                print("[WARNING] Failed to compute homography")
            return None, None, 0
        
        num_inliers = np.sum(mask) if mask is not None else 0
        
        if self.config.verbose:
            inlier_ratio = (num_inliers / len(good_matches)) * 100
            print(f"[INFO] RANSAC found {num_inliers}/{len(good_matches)} inliers ({inlier_ratio:.1f}%)")
            
        return homography_matrix, mask, num_inliers
    
    def warp_image(
        self,
        input_image: np.ndarray,
        template_image: np.ndarray,
        homography_matrix: np.ndarray
    ) -> np.ndarray:
        """
        Warp input image to template coordinate space using perspective transformation
        
        PERSPECTIVE TRANSFORMATION:
        - Maps points from input image to template image using 3x3 homography matrix
        - Handles rotation, scaling, translation, and perspective distortion
        - Uses bilinear interpolation for smooth resampling
        
        Args:
            input_image: Image to align (source)
            template_image: Reference template (target size)
            homography_matrix: Computed homography matrix H (3x3)
            
        Returns:
            Warped image (same size as template)
        """
        height, width = template_image.shape[:2]
        
        # Perspective transformation with bilinear interpolation
        aligned_image = cv2.warpPerspective(
            input_image,
            homography_matrix,
            (width, height),
            flags=cv2.INTER_LINEAR,  # Bilinear interpolation
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(255, 255, 255)  # White border for missing pixels
        )
        
        if self.config.verbose:
            print(f"[INFO] Warped input image to template size: {width}x{height}")
            
        return aligned_image
    
    def calculate_reprojection_error(
        self,
        keypoints_input: List,
        keypoints_template: List,
        good_matches: List,
        homography_matrix: np.ndarray,
        mask: np.ndarray
    ) -> float:
        """
        Calculate mean reprojection error for inlier matches
        
        REPROJECTION ERROR:
        For each inlier match: error = ||H * p_input - p_template||
        Reports mean pixel distance after transformation.
        
        Lower error indicates better alignment quality.
        Target: < 5 pixels
        
        Args:
            keypoints_input: Input image keypoints
            keypoints_template: Template image keypoints
            good_matches: Matched keypoint pairs
            homography_matrix: Estimated homography (3x3)
            mask: Inlier mask from RANSAC (Nx1)
            
        Returns:
            Mean reprojection error in pixels
        """
        errors = []
        
        for i, match in enumerate(good_matches):
            if mask[i]:  # Only consider inliers
                # Get source point and project using homography
                src_pt = np.array([
                    [keypoints_input[match.queryIdx].pt]
                ], dtype=np.float32)
                
                projected_pt = cv2.perspectiveTransform(src_pt, homography_matrix)[0][0]
                dst_pt = np.array(keypoints_template[match.trainIdx].pt)
                
                # Euclidean distance
                error = np.linalg.norm(projected_pt - dst_pt)
                errors.append(error)
        
        mean_error = np.mean(errors) if errors else float('inf')
        
        if self.config.verbose:
            print(f"[INFO] Mean reprojection error: {mean_error:.2f} pixels")
            
        return mean_error
    
    def align(
        self,
        input_image: np.ndarray,
        template_image: np.ndarray
    ) -> AlignmentResult:
        """
        Execute complete Phase 1 alignment pipeline
        
        PIPELINE SEQUENCE:
        1. Feature detection: Detect keypoints in both images
        2. Feature matching: Find corresponding keypoints
        3. Ratio test: Filter weak matches using Lowe's ratio test
        4. Homography: Compute transformation matrix with RANSAC
        5. Warping: Apply perspective transformation
        6. Evaluation: Calculate quality metrics
        
        Args:
            input_image: Document image to align (BGR)
            template_image: Reference template image (BGR)
            
        Returns:
            AlignmentResult with aligned image and quality metrics
        """
        if self.config.verbose:
            print("\n" + "="*70)
            print("PHASE 1: GLOBAL FEATURE-BASED REGISTRATION")
            print("="*70)
        
        # STEP 1.1: Feature Detection and Matching
        if self.config.verbose:
            print("\n[STEP 1.1] Feature Detection and Matching")
        
        keypoints_input, descriptors_input = self.detect_features(input_image)
        keypoints_template, descriptors_template = self.detect_features(template_image)
        
        if descriptors_input is None or descriptors_template is None:
            raise ValueError("Failed to detect features in one or both images")
        
        good_matches = self.match_features(descriptors_input, descriptors_template)
        
        # STEP 1.2: Homography Computation
        if self.config.verbose:
            print("\n[STEP 1.2] Homography Computation (RANSAC)")
        
        homography_matrix, inlier_mask, num_inliers = self.compute_homography(
            keypoints_input, keypoints_template, good_matches
        )
        
        if homography_matrix is None:
            raise RuntimeError("Failed to compute homography matrix")
        
        # Calculate quality metrics
        inlier_ratio = (num_inliers / len(good_matches)) * 100 if good_matches else 0
        reprojection_error = self.calculate_reprojection_error(
            keypoints_input, keypoints_template, good_matches,
            homography_matrix, inlier_mask.flatten()
        )
        
        # STEP 1.3: Image Warping
        if self.config.verbose:
            print("\n[STEP 1.3] Image Warping and Registration")
        
        aligned_image = self.warp_image(input_image, template_image, homography_matrix)
        
        # Print quality assessment
        if self.config.verbose:
            print("\n" + "-"*70)
            print("ALIGNMENT QUALITY METRICS:")
            print("-"*70)
            print(f"  ✓ Inlier ratio: {inlier_ratio:.1f}% (target: >40%)")
            print(f"  ✓ Reprojection error: {reprojection_error:.2f}px (target: <5px)")
            print(f"  ✓ Total matches: {len(good_matches)}")
            print(f"  ✓ Inlier matches: {num_inliers}")
            
            # Alignment quality assessment
            quality_checks = [
                ("Sufficient matches", len(good_matches) >= self.config.min_matches),
                ("Good inlier ratio", inlier_ratio > 40),
                ("Low reprojection error", reprojection_error < 5)
            ]
            
            print("\n  Quality Checks:")
            for check_name, passed in quality_checks:
                status = "✓" if passed else "✗"
                print(f"    {status} {check_name}: {'PASS' if passed else 'FAIL'}")
            
            print("="*70 + "\n")
        
        return AlignmentResult(
            aligned_image=aligned_image,
            homography_matrix=homography_matrix,
            inlier_mask=inlier_mask,
            good_matches=good_matches,
            keypoints_template=keypoints_template,
            keypoints_input=keypoints_input,
            inlier_ratio=inlier_ratio,
            reprojection_error=reprojection_error,
            num_inliers=num_inliers
        )


