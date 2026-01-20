# Label Studio - Render as Component in Existing App

## Summary

**Status:** Not feasible with current Label Studio versions

Embedding Label Studio's annotation UI directly into our React application is no longer supported. The standalone frontend library has been deprecated and archived.

---

## Research Findings

### Label Studio Frontend (Deprecated)

The `@heartexlabs/label-studio` npm package was previously available for embedding the annotation interface into React apps. However:

- **As of Label Studio 1.11.0**, the frontend has been deprecated as a separate library and is no longer supported as a standalone distribution
- The [label-studio-frontend repository](https://github.com/HumanSignal/label-studio-frontend) was **archived on April 18, 2024**
- The last published npm version (1.8.0) is 3+ years old and has reported issues with missing build folders and import errors
- No active maintenance or security updates

### Alternative: Diffgram

Diffgram was evaluated as an alternative annotation platform:

- **Pros:** Supports OIDC/OAuth out of the box (unlike Label Studio Community Edition), enabling seamless SSO
- **Cons:** Also does not support true UI embedding — their recommended approach is deep-linking to tasks with OAuth for seamless login
- **Note:** Diffgram's last major update was September 2023, raising concerns about long-term maintenance

---

## Available Options

### Option 1: Use Label Studio as a Separate Service (Recommended for full annotation features)
- Run Label Studio as a standalone service
- Use the Python SDK to programmatically create tasks
- Configure webhooks to receive completed annotations
- **Limitation:** Users must navigate to a separate app and authenticate separately (Community Edition lacks SSO)

### Option 2: Use Diffgram with OIDC (Recommended if SSO is critical)
- Configure OIDC with your existing identity provider (Keycloak, AWS Cognito, etc.)
- Deep-link users to specific tasks from your app
- Users auto-authenticate via SSO — reduced friction vs Label Studio CE
- **Limitation:** Still a separate UI, not embedded

### Option 3: Build a Custom OCR Correction Component (Recommended for our use case)
- For human-in-the-loop OCR correction, we may not need a full annotation platform
- Build a lightweight React component that displays:
  - The image/document region
  - The extracted OCR text
  - An editable text input for corrections
  - Accept/Reject buttons
- Handle storage via our existing backend
- **Pros:** Fully embedded, no context switching, complete control over UX
- **Cons:** Development effort, limited to text correction (no bounding boxes, polygons, etc.)

### Option 4: Use a React Annotation Library
- Libraries like `react-image-annotate` or `react-image-label` can be embedded directly
- Handle annotation storage ourselves
- **Pros:** True embedding, active (though not heavily maintained) libraries
- **Cons:** Less feature-rich than Label Studio, requires building our own backend logic

---

## Recommendation

For our OCR human-in-the-loop workflow, **Option 3 (custom component)** is likely the best fit:

1. Our primary need is text correction, not complex spatial annotation
2. Keeps users in our app with no context switching
3. Avoids dependency on deprecated/archived libraries
4. Full control over UX and integration with our pipeline

If we later need full annotation capabilities (bounding boxes, polygons, multi-user workflows), we should revisit **Option 2 (Diffgram + OIDC)** for the SSO benefits over Label Studio Community Edition.

---

## References

- [Label Studio Frontend Deprecation Notice](https://labelstud.io/guide/frontend.html)
- [Archived GitHub Repository](https://github.com/HumanSignal/label-studio-frontend)
- [Diffgram OIDC Documentation](https://diffgram.readme.io/docs/oidc)
- [Diffgram App Integration Guide](https://diffgram.readme.io/docs/use-diffgram-with-your-apps)
