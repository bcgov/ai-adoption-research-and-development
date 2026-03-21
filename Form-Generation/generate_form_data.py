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
    return date.strftime(format_str)

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

def generate_data():
  test_data = {}
  
  # Checkboxes Section
  # For each pair of checkboxes, we'll have percentage-based rules to determine
  # if the Yes or No should be checked

  # In need of assistance
  if roll100(70):
      test_data['checkbox_need_assistance_yes'] = True
  else:
      test_data['checkbox_need_assistance_no'] = True
			
  # Received assets
  if roll100(50):
      test_data['checkbox_family_assets_yes'] = True
  else:
      test_data['checkbox_family_assets_no'] = True

  # Shelter cost change
  if roll100(50):
      test_data['checkbox_shelter_yes'] = True
  else:
      test_data['checkbox_shelter_no'] = True

  # Dependants
  if roll100(50):
      test_data['checkbox_dependants_yes'] = True
  else:
      test_data['checkbox_dependants_no'] = True

  # Applicant Check Boxes
  # Employment Changes
  if roll100(50):
       test_data['checkbox_employment_changes_yes'] = True
  else:
       test_data['checkbox_employment_changes_no'] = True
  
  # Attending School
  if roll100(50):
       test_data['checkbox_school_yes'] = True
  else:
       test_data['checkbox_school_no'] = True
  
  # Looking for work
  if roll100(50):
       test_data['checkbox_work_yes'] = True
  else:
       test_data['checkbox_work_no'] = True

  # Moved
  if roll100(50):
       test_data['checkbox_moved_yes'] = True
  else:
       test_data['checkbox_moved_no'] = True

  # Warrants
  if roll100(20):
       test_data['checkbox_warrant_yes'] = True
  else:
       test_data['checkbox_warrant_no'] = True

  # Explain changes
  test_data['explain_changes'] = generate_short_text()

  # Spouse Check Boxes
  # Roll to see if they have a spouse
  hasSpouse = roll100(50)
  if (hasSpouse):
    # Employment Changes
    if roll100(50):
        test_data['checkbox_employment_changes_spouse_yes'] = True
    else:
        test_data['checkbox_employment_changes_spouse_no'] = True
    
    # Attending School
    if roll100(50):
        test_data['checkbox_school_spouse_yes'] = True
    else:
        test_data['checkbox_school_spouse_no'] = True
    
    # Looking for work
    if roll100(50):
        test_data['checkbox_work_spouse_yes'] = True
    else:
        test_data['checkbox_work_spouse_no'] = True

    # Moved
    if roll100(50):
        test_data['checkbox_moved_spouse_yes'] = True
    else:
        test_data['checkbox_moved_spouse_no'] = True

    # Warrants
    if roll100(20):
        test_data['checkbox_warrant_spouse_yes'] = True
    else:
        test_data['checkbox_warrant_spouse_no'] = True

  # Income Section
  # This can help identify fields: https://raw.githubusercontent.com/bcgov/ai-adoption-research-and-development/refs/heads/main/Template-alignment/outputs/visualizations/extraction_visualization.jpg
  # For each field, we'll roll to see if anything is filled here
  # If it is, we roll to see if it's just a 0.
  def valueOrZero():
       # Is filled?
       if roll100(30):
            # Is that a non-zero amount?
            return generate_money_value() if roll100(80) else 0
       else:
            return None
       
  # Applicant Area
  for i in range(1, 19):
      test_data[f'income{i}'] = valueOrZero()
  # Spouse
  if (hasSpouse):
    # One less, b/c that field is intended blank
    for i in range(1, 18):
      test_data[f'spouse_income{i}'] = valueOrZero()

  # Declaration Section
  # Applicant
  name = generate_full_name()
  test_data['signature'] = generate_signature_from_name(name)
  test_data['date'] = generate_date()
  test_data['name'] = name
  test_data['phone'] = generate_telephone()
  test_data['sin'] = generate_sin()

  # Spouse
  if (hasSpouse):
    spouse_name = generate_full_name()
    test_data['spouse_signature'] = generate_signature_from_name(spouse_name)
    test_data['spouse_date'] = generate_date()
    test_data['spouse_name'] = spouse_name
    test_data['spouse_phone'] = generate_telephone()
    test_data['spouse_sin'] = generate_sin()

  # Return the results
  return test_data
