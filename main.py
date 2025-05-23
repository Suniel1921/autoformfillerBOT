from playwright.sync_api import sync_playwright
import json
import time
from datetime import datetime, timedelta

def solve_captcha(page):
    """
    Prompts the user to manually enter captcha text.
    """
    print("Please enter the captcha text manually (automation limited, provide text from image):")
    return input()

def is_date_available(page, target_day, month_index=0):
    """
    Check if a specific date is available in the current calendar view.
    Available dates have an <a> tag with draggable="false".
    """
    try:
        # Wait for the calendar table to render
        page.wait_for_selector('table.ui-datepicker-calendar', timeout=15000)
        time.sleep(2)  # Extra delay to ensure rendering

        # Log the calendar HTML for debugging
        calendar_html = page.query_selector('table.ui-datepicker-calendar').inner_html()
        print(f"Calendar HTML for month index {month_index}:\n{calendar_html}")

        # Selector for available date (td containing a with draggable="false")
        date_cell_selector = f'td a[draggable="false"]:text-is("{target_day}")'
        available_date_elements = page.locator(date_cell_selector).all()

        print(f"Found {len(available_date_elements)} elements for day {target_day} with <a> tag and draggable='false'.")
        for date_element in available_date_elements:
            if date_element.is_enabled():
                print(f"Date {target_day} is available in month index {month_index}.")
                return date_element

        # Check for unavailable dates (span with ui-state-disabled)
        unavailable_selector = f'td span.ui-state-disabled:text-is("{target_day}")'
        unavailable_elements = page.locator(unavailable_selector).all()
        if unavailable_elements:
            print(f"Date {target_day} is unavailable in month index {month_index}.")
        else:
            print(f"Date {target_day} not found in month index {month_index}.")

        return None
    except Exception as e:
        print(f"Error checking date availability for day {target_day}: {e}")
        return None

def go_to_next_month(page):
    """Navigate to the next month in the date picker."""
    try:
        # Ensure the next button is visible
        next_button_selector = '.ui-datepicker-next-icon.pi.pi-chevron-right'
        page.wait_for_selector(next_button_selector, state="visible", timeout=5000)
        next_button = page.query_selector(next_button_selector)
        if next_button and next_button.is_visible():
            next_button.click()
            print("Clicked 'Next month' button.")
            time.sleep(2)  # Wait for the next month to load
            return True
        else:
            print("Next month button not found or not visible.")
            return False
    except Exception as e:
        print(f"Error navigating to next month: {e}")
        return False

def check_for_available_date(page):
    """
    Iterate through dates starting from the current date (May 23, 2025) and future months.
    Select the first available date with available time slots.
    Checks all days in the current month before moving to the next.
    """
    print("Attempting to select an available appointment date.")
    date_selected = False
    max_months_to_check = 7

    # Start from the current date (May 23, 2025)
    current_date = datetime.now()
    start_day = current_date.day  # Start from today (23rd)
    max_days_in_month = 31  # Maximum days to check per month

    for month_advance_count in range(max_months_to_check):
        print(f"Checking month (iteration {month_advance_count + 1} of {max_months_to_check})")

        # Check for "no available slots" message
        no_slots_message_locator = page.locator('text="There are no available slots at the moment"')
        if no_slots_message_locator.is_visible(timeout=2000):
            print(f"No slots available in the current calendar view. Clicking 'Next month'.")
            if not go_to_next_month(page):
                raise Exception("Failed to navigate to the next month.")
            continue

        # Determine the starting day for the current month
        start_day_of_search = start_day if month_advance_count == 0 else 1

        # Iterate through all days in the current month
        days_checked = []
        for day_to_check in range(start_day_of_search, max_days_in_month + 1):
            days_checked.append(day_to_check)
            available_date = is_date_available(page, str(day_to_check), month_index=month_advance_count)
            if available_date:
                try:
                    available_date.click()
                    print(f"Selected date: {day_to_check} in month index {month_advance_count}")
                    
                    # Check if time slots are available for the selected date
                    time_slot_selector = 'mat-chip:not(.mat-chip-disabled)'
                    page.wait_for_selector('mat-chip-list', state="visible", timeout=5000)
                    available_time_slots = page.locator(time_slot_selector).all()
                    if not available_time_slots:
                        print(f"No available time slots for date {day_to_check}. Moving to next month.")
                        # Reopen the date picker to navigate to the next month
                        date_input = page.query_selector('input[formcontrolname="appointmentDate"]')
                        if date_input and date_input.is_visible():
                            date_input.click()
                            print("Reopened date picker to navigate to next month.")
                        else:
                            print("Could not reopen date picker.")
                            raise Exception("Failed to reopen date picker to navigate to next month.")
                        break  # Break the day loop to move to the next month
                    else:
                        date_selected = True
                        break  # Exit the day loop since we found a date with available time slots
                except Exception as e:
                    print(f"Error selecting date {day_to_check}: {e}")
            print(f"Checked day {day_to_check} in month index {month_advance_count}")

        if date_selected:
            print(f"Available date found after checking days: {days_checked}")
            break

        print(f"No available dates found after checking days {days_checked} in month index {month_advance_count}. Clicking 'Next month'.")
        if not go_to_next_month(page):
            raise Exception("Failed to navigate to the next month.")

    if not date_selected:
        raise Exception("Failed to select an available date after checking multiple months.")

    return date_selected

def main():
    """
    Automates the process of filling out a passport pre-enrollment form.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.on("dialog", lambda dialog: dialog.accept())
        
        try:
            with open('data.json', 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print("Error: data.json not found. Please create a data.json file with your form data.")
            browser.close()
            return

        max_attempts = 2
        success = False

        for attempt in range(max_attempts):
            try:
                print(f"Attempt {attempt + 1}: Step 1: Navigating to home page")
                page.goto('https://emrtds.nepalpassport.gov.np/')
                
                login_required = page.query_selector('text="Log In"') or page.query_selector('text="Login"')
                if login_required:
                    print("Login required, please log in manually.")
                    raise Exception("Login required, stopping for manual intervention.")
                
                print("Step 2: Clicking on First Issuance")
                page.click('text="First Issuance"')
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/request-service', timeout=20000)
                
                print("Step 3: Selecting passport type")
                page.wait_for_selector('label:has-text("Ordinary 34 pages")', timeout=15000)
                radio_selector = 'input[type="radio"] + label:has-text("Ordinary 34 pages")'
                is_selected = page.eval_on_selector(radio_selector, 'element => element.previousElementSibling.checked')
                if not is_selected:
                    page.click(radio_selector)
                    print("Selected Ordinary 34 pages")
                else:
                    print("Ordinary 34 pages is already selected")
                time.sleep(2)
                
                print("Step 4: Clicking Proceed button")
                proceed_selector = 'a:has-text("Proceed")'
                page.wait_for_selector(proceed_selector, state="visible", timeout=20000)
                page.evaluate('element => element.scrollIntoView()', page.query_selector(proceed_selector))
                
                for click_attempt in range(3):
                    try:
                        page.click(proceed_selector)
                        print(f"Successfully clicked Proceed on attempt {click_attempt + 1}")
                        break
                    except Exception as e:
                        print(f"Click attempt {click_attempt + 1} failed: {e}, retrying...")
                        time.sleep(2)
                else:
                    raise Exception("Failed to click Proceed button after 3 attempts")
                
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(5)
                
                print("Taking screenshot after clicking Proceed")
                page.screenshot(path='post_proceed.png')
                
                print("Page content after clicking Proceed:")
                print(page.content())
                
                current_url = page.url
                if current_url == 'https://emrtds.nepalpassport.gov.np/':
                    print("Detected redirect to homepage, attempting to restart...")
                    continue
                
                print("Step 5: Agreeing to terms")
                agree_selector = 'a:has-text("I agree स्वीकृत छ")'
                page.wait_for_selector(agree_selector, state="visible", timeout=15000)
                page.click(agree_selector)
                print("Clicked 'I agree' on the modal")
                
                print("Step 6: Filling appointment details")
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/appointment', timeout=30000)
                
                print("Waiting for appointment form elements")
                page.wait_for_selector('#mat-select-0', state="visible", timeout=20000)
                page.wait_for_selector('#mat-select-1', state="visible", timeout=20000)
                
                print("Selecting appointment country as Other")
                page.click('#mat-select-0')
                page.wait_for_selector('mat-option', state="visible", timeout=10000)
                page.click('mat-option span:text("Other")')
                
                print("Selecting appointment location as NE, Tokyo")
                page.click('#mat-select-1')
                page.wait_for_selector('mat-option', state="visible", timeout=10000)
                page.click('mat-option span:text("NE, Tokyo")')
                
                # Add a small delay to ensure dropdown selections are processed
                time.sleep(2)
                
                # Trigger the date picker with multiple attempts
                print("Attempting to trigger the date picker")
                date_input_selectors = [
                    'input[formcontrolname="appointmentDate"]',
                    'mat-form-field input',
                    'mat-datepicker-toggle',
                    'input[type="date"]',
                    '[placeholder*="Select Date"]',
                    'label:has-text("Appointment Date")',
                    'mat-label:has-text("Appointment Date") + input'
                ]
                date_input_triggered = False
                for selector in date_input_selectors:
                    try:
                        date_input = page.query_selector(selector)
                        if date_input and date_input.is_visible():
                            date_input.click()
                            print(f"Clicked date input using selector: {selector}")
                            date_input_triggered = True
                            break
                    except Exception as e:
                        print(f"Failed to click selector {selector}: {e}")
                if not date_input_triggered:
                    print("No specific date input found, trying generic click on form fields")
                    try:
                        page.click('form mat-form-field, form button, form input', timeout=10000)
                    except Exception as e:
                        print(f"Generic click failed: {e}")
                
                # Wait for the calendar to appear after triggering
                print("Waiting for the calendar to appear")
                page.wait_for_selector('table.ui-datepicker-calendar', state="visible", timeout=15000)
                
                print("Logging appointment form HTML for debugging:")
                appointment_form = page.query_selector('form')
                if appointment_form:
                    print(appointment_form.inner_html())
                else:
                    print("Appointment form not found, logging entire page content:")
                    print(page.content())

                print("Pausing for 30 seconds to allow manual inspection...")
                print("Inspect the calendar (e.g., right-click June 4 and select 'Inspect').")
                time.sleep(30)

                if not check_for_available_date(page):
                    raise Exception("Failed to select an available date.")
                
                print("Selecting appointment time")
                time_slot_selector = 'mat-chip:not(.mat-chip-disabled)'
                page.wait_for_selector('mat-chip-list', state="visible", timeout=10000)
                available_time_slots = page.locator(time_slot_selector).all()
                if not available_time_slots:
                    raise Exception("No available time slots found for the selected date.")
                
                available_times = ["11:30", "12:00"]
                for time_value in available_times:
                    try:
                        time_slot = page.locator(f'mat-chip:not(.mat-chip-disabled):text-is("{time_value}")')
                        if time_slot.is_visible():
                            time_slot.click()
                            print(f"Selected time: {time_value}")
                            break
                    except Exception:
                        print(f"Time {time_value} not available, trying next...")
                else:
                    print("Neither 11:30 nor 12:00 available, proceeding with first available time slot.")
                    available_time_slots[0].click()
                    print(f"Selected first available time slot: {available_time_slots[0].inner_text()}")
                
                print("Solving captcha")
                captcha_text = solve_captcha(page)
                page.fill('input[name="text"]', captcha_text)  # Updated selector based on HTML
                page.click('button:has-text("Next")')
                
                print("Step 7: Filling request form")
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/request-form', timeout=30000)
                
                fill_demographic_info(page, data)
                fill_citizenship_info(page, data)
                fill_applicant_contact(page, data)
                fill_emergency_contact(page, data)
                
                print("Step 8: Taking final screenshot")
                try:
                    page.screenshot(path='final_page.png', timeout=10000)
                except Exception as e:
                    print(f"Failed to take final screenshot: {e}")
                
                print("Form submission completed successfully!")
                success = True
                break
                
            except Exception as e:
                print(f"An error occurred during the process: {e}")
                try:
                    page.screenshot(path='error_page.png', timeout=10000)
                except Exception as e_shot:
                    print(f"Failed to take error screenshot: {e_shot}")
                print("Page content on error:")
                print(page.content())
                
                if attempt < max_attempts - 1:
                    print("Retrying due to error...")
                    time.sleep(2)
                    continue
                else:
                    print("Max attempts reached, stopping.")
                    break
        
        if not success:
            print("Failed to complete the process after all attempts.")
        browser.close()

def fill_demographic_info(page, data):
    """Fills the demographic information section."""
    print("Filling Demographic Information")
    page.fill('#last_name', data['last_name'])
    page.fill('#first_name', data['first_name'])
    if data['gender'].lower() == 'male':
        page.check('#gender_male')
    elif data['gender'].lower() == 'female':
        page.check('#gender_female')
    else:
        page.check('#gender_other')
    page.fill('#dob_ad', data['dob_ad'])
    page.fill('#dob_bs', data['dob_bs'])
    page.select_option('#place_of_birth_district', label=data['place_of_birth_district'])
    page.select_option('#birth_country', label=data['birth_country'])
    page.select_option('#nationality', label=data['nationality'])
    page.fill('#father_last_name', data['father_last_name'])
    page.fill('#father_first_name', data['father_first_name'])
    page.fill('#mother_last_name', data['mother_last_name'])
    page.fill('#mother_first_name', data['mother_first_name'])
    page.click('text="Next"')

def fill_citizenship_info(page, data):
    """Fills the citizenship information section."""
    print("Filling Citizenship Information")
    page.fill('#nin', data['nin'])
    page.fill('#citizenship_number', data['citizenship_number'])
    page.fill('#citizenship_issue_date_bs', data['citizenship_issue_date_bs'])
    page.select_option('#citizenship_issue_district', label=data['citizenship_issue_district'])
    page.click('text="Next"')

def fill_applicant_contact(page, data):
    """Fills the applicant's contact details."""
    print("Filling Applicant Contact Details")
    page.fill('#mobile_number', data['mobile_number'])
    page.fill('#email', data['email'])
    page.fill('#main_address_house_number', data['main_address_house_number'])
    page.fill('#main_address_street', data['main_address_street'])
    page.fill('#main_address_ward', data['main_address_ward'])
    page.select_option('#main_address_country', label=data['main_address_country'])
    page.select_option('#main_address_province', label=data['main_address_province'])
    page.select_option('#main_address_district', label=data['main_address_district'])
    page.select_option('#main_address_municipality', label=data['main_address_municipality'])
    page.click('text="Next"')

def fill_emergency_contact(page, data):
    """Fills the emergency contact details."""
    print("Filling Emergency Contact Details")
    page.fill('#emergency_last_name', data['emergency_contact_last_name'])
    page.fill('#emergency_first_name', data['emergency_contact_first_name'])
    page.fill('#emergency_house_number', data['emergency_contact_house_number'])
    page.fill('#emergency_street', data['emergency_contact_street'])
    page.fill('#emergency_ward', data['emergency_contact_ward'])
    page.select_option('#emergency_province', label=data['emergency_contact_province'])
    page.select_option('#emergency_district', label=data['emergency_contact_district'])
    page.select_option('#emergency_municipality', label=data['emergency_contact_municipality'])
    page.select_option('#emergency_country', label=data['emergency_contact_country'])
    page.fill('#emergency_phone', data['emergency_contact_phone'])
    page.fill('#emergency_email', data['emergency_contact_email'])
    page.click('text="Next"')

if __name__ == '__main__':
    main()



    # dfdfdfdfdfdfddfsfsfsadfasdfsadfsdfsdfs