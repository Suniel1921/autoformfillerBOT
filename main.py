from playwright.sync_api import sync_playwright
import json
import time

def solve_captcha(page):
    print("Please enter the captcha text manually:")
    return input()

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Set headless=True for production
        page = browser.new_page()
        
        # Handle potential pop-ups or alerts
        page.on("dialog", lambda dialog: dialog.accept())
        
        # Load data from JSON
        with open('data.json', 'r') as f:
            data = json.load(f)
        
        max_attempts = 2  # Allow 2 attempts to proceed in case of redirect
        success = False
        
        for attempt in range(max_attempts):
            try:
                # Step 1: Navigate to home page
                print(f"Attempt {attempt + 1}: Step 1: Navigating to home page")
                page.goto('https://emrtds.nepalpassport.gov.np/')
                
                # Check for login requirement (if any)
                login_required = page.query_selector('text="Log In"') or page.query_selector('text="Login"')
                if login_required:
                    print("Login required, please log in manually or add login credentials to the script.")
                    raise Exception("Login required, stopping for manual intervention.")
                
                # Step 2: Click on First Issuance
                print("Step 2: Clicking on First Issuance")
                page.click('text="First Issuance"')
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/request-service', timeout=20000)
                
                # Step 3: Select passport type
                print("Step 3: Selecting passport type")
                page.wait_for_selector('label:has-text("Ordinary 34 pages")', timeout=15000)
                radio_selector = 'input[type="radio"] + label:has-text("Ordinary 34 pages")'
                is_selected = page.eval_on_selector(radio_selector, 'element => element.previousElementSibling.checked')
                if not is_selected:
                    page.click(radio_selector)
                    print("Selected Ordinary 34 pages")
                else:
                    print("Ordinary 34 pages is already selected")
                time.sleep(2)  # Brief pause to ensure selection is processed
                
                # Step 4: Click Proceed button
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
                
                # Wait for the next page or preloader to disappear
                page.wait_for_load_state('networkidle', timeout=30000)
                time.sleep(5)  # Extra delay to ensure page transition
                
                # Take a screenshot after clicking Proceed to debug
                print("Taking screenshot after clicking Proceed")
                page.screenshot(path='post_proceed.png')
                
                # Debug: Print page content to check for error messages
                print("Page content after clicking Proceed:")
                print(page.content())
                
                # Check for unexpected redirect to homepage
                current_url = page.url
                if current_url == 'https://emrtds.nepalpassport.gov.np/':
                    print("Detected redirect to homepage, attempting to restart...")
                    continue  # Restart the loop if redirected
                
                # Step 5: Handle agreement modal
                print("Step 5: Agreeing to terms")
               
                proceed_selector = 'a:has-text("I agree स्वीकृत छ")'
                page.click('text=' "I agree स्वीकृत छ ")
                
                # Step 6: Fill appointment details
                print("Step 6: Filling appointment details")
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/appointment', timeout=30000)
                page.select_option('#mat-select-0', label=data['appointment_country'])
                page.select_option('#mat-select-1', label=data['appointment_location'])
                
                # Select date (assuming format 'YYYY-MM-DD')
                print("Selecting appointment date")
                page.click('#datePicker')
                day = int(data['appointment_date'].split('-')[2])
                page.click(f'text="{day}"')
                
                # Select time
                print("Selecting appointment time")
                page.select_option('#timeSlot', label=data['appointment_time'])
                
                # Solve captcha
                print("Solving captcha")
                captcha_text = solve_captcha(page)
                page.fill('#captchaInput', captcha_text)
                page.click('text="Next"')
                
                # Step 7: Fill request form
                print("Step 7: Filling request form")
                page.wait_for_url('https://emrtds.nepalpassport.gov.np/request-form', timeout=30000)
                
                # Fill each section
                fill_demographic_info(page, data)
                fill_citizenship_info(page, data)
                fill_applicant_contact(page, data)
                fill_emergency_contact(page, data)
                
                # Step 8: Save screenshot
                print("Step 8: Taking screenshot")
                page.screenshot(path='final_page.png')
                print("Form submission completed successfully!")
                success = True
                break  # Exit loop if successful
                
            except Exception as e:
                print(f"Error occurred: {e}")
                page.screenshot(path='error_page.png')
                if attempt < max_attempts - 1:
                    print("Retrying due to error...")
                    time.sleep(2)
                    continue
                else:
                    print("Max attempts reached, stopping.")
                    break
        
        # Close browser only after all attempts are done
        if not success:
            print("Failed to complete the process after all attempts.")
        browser.close()

def fill_demographic_info(page, data):
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
    print("Filling Citizenship Information")
    page.fill('#nin', data['nin'])
    page.fill('#citizenship_number', data['citizenship_number'])
    page.fill('#citizenship_issue_date_bs', data['citizenship_issue_date_bs'])
    page.select_option('#citizenship_issue_district', label=data['citizenship_issue_district'])
    page.click('text="Next"')

def fill_applicant_contact(page, data):
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