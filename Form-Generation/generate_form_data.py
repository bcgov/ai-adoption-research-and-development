from datetime import datetime
import random
from faker import Faker

faker = Faker()

def roll100(percentage):
	"""
	Returns True with probability equal to percentage (0-100), else False.
	"""
	return random.uniform(0, 100) < percentage

def generate_money_value(min_value=1, max_value=10000):
    value = random.uniform(min_value, max_value)
    # Randomly decide on formatting style
    show_cents = roll100(70)  # 70% chance to show cents
    show_comma = roll100(50)  # 50% chance to show comma
    if show_cents:
        fmt = ",.2f" if show_comma else ".2f"
    else:
        fmt = ",.0f" if show_comma else ".0f"
    return format(value, fmt)

def generate_full_name():
	return faker.name()

def generate_telephone():
  patterns = ["###-###-###", "### ### ###", "#########", "(###) ### ###", "(###) ###-###", "###.###.###"]
  pattern = random.choice(patterns)
  digits = [str(random.randint(0, 9)) for _ in range(pattern.count('#'))]
  result = ""
  digit_idx = 0
  for char in pattern:
    if char == '#':
        result += digits[digit_idx]
        digit_idx += 1
    else:
        result += char
  return result

def generate_short_text(max_length=20):
	text = faker.sentence(nb_words=8)
	return text if len(text) <= max_length else text[:max_length]

def generate_long_text(min_words=30, max_words=60):
	"""
	Generate a longer text string suitable for multi-line fields.
	"""
	num_words = random.randint(min_words, max_words)
	# Generate multiple sentences to create natural paragraph-like text
	sentences = []
	words_remaining = num_words
	while words_remaining > 0:
		sentence_words = min(random.randint(8, 15), words_remaining)
		sentence = faker.sentence(nb_words=sentence_words)
		sentences.append(sentence)
		words_remaining -= sentence_words
	return " ".join(sentences)

def generate_date(format_str=None):
    """
    Generate a date string in a variable format.
    If format_str is None, randomly choose a common format.
    """
    main_format = "%Y-%b-%d"  # yyyy-mmm-dd
    other_formats = [
        "%Y-%m-%d",  # yyyy-mm-dd
        "%m-%d-%y",  # mm-dd-yy
        "%d-%m-%Y",  # dd-mm-yyyy
        "%d/%m/%Y",  # dd/mm/yyyy
        "%m/%d/%Y",  # mm/dd/yyyy
    ]
    if format_str is None:
        if roll100(70):
            format_str = main_format
        else:
            format_str = random.choice(other_formats)
    date = faker.date_this_century()
    return date.strftime(format_str), date.strftime("%Y-%m-%d")

def generate_sin(pattern=None):
    """
    Generate a number string in a given pattern.
    Supported patterns: ###-###-###, ### ### ###, ########
    If pattern is None, randomly choose one.
    """
    patterns = ["###-###-###", "### ### ###", "#########"]
    if pattern is None:
        pattern = random.choice(patterns)
    digits = [str(random.randint(0, 9)) for _ in range(pattern.count('#'))]
    result = ""
    digit_idx = 0
    for char in pattern:
        if char == '#':
            result += digits[digit_idx]
            digit_idx += 1
        else:
            result += char
    return result

def generate_signature_from_name(full_name):
    """
    Generate a signature-like string from a full name.
    Example: 'John Doe' -> 'J. Doe' or 'John D.'
    Randomly choose a style for variety.
    """
    parts = full_name.split()
    if len(parts) < 2:
        return full_name
    first, last = parts[0], parts[-1]
    styles = [
        f"{first[0]}. {last}",
        f"{first} {last[0]}.",
        f"{first} {last}",
        f"{first[0]}. {last[0]}."
    ]
    return random.choice(styles)

APPLICANT_INCOME_FIELDS = [
    "applicant_net_employment_income",
    "applicant_employment_insurance",
    "applicant_spousal_support_alimony",
    "applicant_child_support",
    "applicant_workbc_financial_support",
    "applicant_student_funding_loans_bursaries",
    "applicant_rental_income",
    "applicant_room_board_income",
    "applicant_workers_compensation",
    "applicant_private_pensions_retirement_disability",
    "applicant_oas_gis",
    "applicant_trust_income",
    "applicant_canada_pension_plan_cpp",
    "applicant_tax_credits_gst_credit",
    "applicant_child_tax_benefits",
    "applicant_income_tax_refund",
    "applicant_other_income_money_received",
    "applicant_income_of_dependent_children",
]

SPOUSE_INCOME_FIELDS = [
    "spouse_net_employment_income",
    "spouse_employment_insurance",
    "spouse_spousal_support_alimony",
    "spouse_child_support",
    "spouse_workbc_financial_support",
    "spouse_student_funding_loans_bursaries",
    "spouse_rental_income",
    "spouse_room_board_income",
    "spouse_workers_compensation",
    "spouse_private_pensions_retirement_disability",
    "spouse_oas_gis",
    "spouse_trust_income",
    "spouse_canada_pension_plan_cpp",
    "spouse_tax_credits_gst_credit",
    "spouse_child_tax_benefits",
    "spouse_income_tax_refund",
    "spouse_other_income_money_received",
    # spouse_income_of_dependent_children is intentionally excluded — always blank on the form
]

ALL_INCOME_FIELDS = set(APPLICANT_INCOME_FIELDS + SPOUSE_INCOME_FIELDS)

def generate_data(complete_fill=False, explain_min_words=30, explain_max_words=60):
  """
  Generate form data with realistic values.

  Args:
    complete_fill: If True, ensures all fields are filled with proper data.
                   If False, uses probabilistic rules (default behavior).
    explain_min_words: When complete_fill, min word count for explain_changes paragraph.
    explain_max_words: When complete_fill, max word count for explain_changes paragraph.
  """
  test_data = {}
  
  # Checkboxes Section
  # For each pair of checkboxes, we'll have percentage-based rules to determine
  # if the Yes or No should be checked

  selected = "selected"
  unselected = "unselected"

  # In need of assistance
  if roll100(70):
      test_data['checkbox_need_assistance_yes'] = selected
      test_data['checkbox_need_assistance_no'] = unselected
  else:
      test_data['checkbox_need_assistance_yes'] = unselected
      test_data['checkbox_need_assistance_no'] = selected

  # Received assets
  if roll100(50):
      test_data['checkbox_family_assets_yes'] = selected
      test_data['checkbox_family_assets_no'] = unselected
  else:
      test_data['checkbox_family_assets_yes'] = unselected
      test_data['checkbox_family_assets_no'] = selected

  # Shelter cost change
  if roll100(50):
      test_data['checkbox_shelter_yes'] = selected
      test_data['checkbox_shelter_no'] = unselected
  else:
      test_data['checkbox_shelter_yes'] = unselected
      test_data['checkbox_shelter_no'] = selected

  # Dependants
  if roll100(50):
      test_data['checkbox_dependants_yes'] = selected
      test_data['checkbox_dependants_no'] = unselected
  else:
      test_data['checkbox_dependants_yes'] = unselected
      test_data['checkbox_dependants_no'] = selected

  # Applicant Check Boxes
  # Employment Changes
  if roll100(50):
       test_data['checkbox_employment_changes_yes'] = selected
       test_data['checkbox_employment_changes_no'] = unselected
  else:
       test_data['checkbox_employment_changes_yes'] = unselected
       test_data['checkbox_employment_changes_no'] = selected

  # Attending School
  if roll100(50):
       test_data['checkbox_school_yes'] = selected
       test_data['checkbox_school_no'] = unselected
  else:
       test_data['checkbox_school_yes'] = unselected
       test_data['checkbox_school_no'] = selected

  # Looking for work
  if roll100(50):
       test_data['checkbox_work_yes'] = selected
       test_data['checkbox_work_no'] = unselected
  else:
       test_data['checkbox_work_yes'] = unselected
       test_data['checkbox_work_no'] = selected

  # Moved
  if roll100(50):
       test_data['checkbox_moved_yes'] = selected
       test_data['checkbox_moved_no'] = unselected
  else:
       test_data['checkbox_moved_yes'] = unselected
       test_data['checkbox_moved_no'] = selected

  # Warrants
  if roll100(20):
       test_data['checkbox_warrant_yes'] = selected
       test_data['checkbox_warrant_no'] = unselected
  else:
       test_data['checkbox_warrant_yes'] = unselected
       test_data['checkbox_warrant_no'] = selected

  # Explain changes
  if complete_fill:
      test_data['explain_changes'] = generate_long_text(min_words=explain_min_words, max_words=explain_max_words)
  else:
      test_data['explain_changes'] = generate_short_text()

  # Spouse Check Boxes
  # Roll to see if they have a spouse
  # In complete_fill mode, always include spouse
  hasSpouse = True if complete_fill else roll100(50)
  if (hasSpouse):
    # Employment Changes
    if roll100(50):
        test_data['checkbox_employment_changes_spouse_yes'] = selected
        test_data['checkbox_employment_changes_spouse_no'] = unselected
    else:
        test_data['checkbox_employment_changes_spouse_yes'] = unselected
        test_data['checkbox_employment_changes_spouse_no'] = selected

    # Attending School
    if roll100(50):
        test_data['checkbox_school_spouse_yes'] = selected
        test_data['checkbox_school_spouse_no'] = unselected
    else:
        test_data['checkbox_school_spouse_yes'] = unselected
        test_data['checkbox_school_spouse_no'] = selected

    # Looking for work
    if roll100(50):
        test_data['checkbox_work_spouse_yes'] = selected
        test_data['checkbox_work_spouse_no'] = unselected
    else:
        test_data['checkbox_work_spouse_yes'] = unselected
        test_data['checkbox_work_spouse_no'] = selected

    # Moved
    if roll100(50):
        test_data['checkbox_moved_spouse_yes'] = selected
        test_data['checkbox_moved_spouse_no'] = unselected
    else:
        test_data['checkbox_moved_spouse_yes'] = unselected
        test_data['checkbox_moved_spouse_no'] = selected

    # Warrants
    if roll100(20):
        test_data['checkbox_warrant_spouse_yes'] = selected
        test_data['checkbox_warrant_spouse_no'] = unselected
    else:
        test_data['checkbox_warrant_spouse_yes'] = unselected
        test_data['checkbox_warrant_spouse_no'] = selected

  # Income Section
  # This can help identify fields: https://raw.githubusercontent.com/bcgov/ai-adoption-research-and-development/refs/heads/main/Template-alignment/outputs/visualizations/extraction_visualization.jpg
  # For each field, we'll roll to see if anything is filled here
  # If it is, we roll to see if it's just a 0.
  def valueOrZero():
       if complete_fill:
            # In complete fill mode, always return a non-zero money value
            return generate_money_value()
       else:
            # Is filled?
            if roll100(30):
                 # Is that a non-zero amount?
                 return generate_money_value() if roll100(80) else 0
            else:
                 return None
       
  # Applicant Area
  for field_name in APPLICANT_INCOME_FIELDS:
      test_data[field_name] = valueOrZero()
  # Spouse
  if (hasSpouse):
    for field_name in SPOUSE_INCOME_FIELDS:
      test_data[field_name] = valueOrZero()

  # Declaration Section
  # Applicant
  name = generate_full_name()
  test_data['signature'] = generate_signature_from_name(name)
  date_display, date_iso = generate_date()
  test_data['date'] = date_display
  test_data['_date_iso'] = date_iso
  test_data['name'] = name
  test_data['phone'] = generate_telephone()
  test_data['sin'] = generate_sin()

  # Spouse
  if (hasSpouse):
    spouse_name = generate_full_name()
    test_data['spouse_signature'] = generate_signature_from_name(spouse_name)
    spouse_date_display, spouse_date_iso = generate_date()
    test_data['spouse_date'] = spouse_date_display
    test_data['_spouse_date_iso'] = spouse_date_iso
    test_data['spouse_name'] = spouse_name
    test_data['spouse_phone'] = generate_telephone()
    test_data['spouse_sin'] = generate_sin()

  # Return the results
  return test_data
