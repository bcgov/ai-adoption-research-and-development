package ocr.validation

# Main validation entry point
default allowed = false

# Allow if both data quality and business rules pass
allowed {
    data ocr.validation.data_quality.allowed
    data ocr.validation.business_rules.allowed
}

# Aggregate violations from all policy packages
violations[violation] {
    violation := data ocr.validation.data_quality.violations[_]
}

violations[violation] {
    violation := data ocr.validation.business_rules.violations[_]
}

# Extract warnings (violations with severity warning)
warnings[violation] {
    violation := violations[_]
    violation.severity == "warning"
}

# Get data quality score
dataQualityScore = score {
    score := data ocr.validation.data_quality.dataQualityScore
}

# Get business rule compliance
businessRuleCompliance = compliance {
    compliance := data ocr.validation.business_rules.businessRuleCompliance
}

