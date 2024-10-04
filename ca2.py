import csv
import re
import bcrypt
import requests
from datetime import datetime, timedelta
import getpass
import random
import string

userCsv = '/content/sample_data/regno.csv'
historyCsv = '/content/sample_data/history.csv'
apiKey = 'df3b1dd035e34373bcddb3cb704075d3'
maxLoginAttempts = 5

def validateEmail(email):
    emailRegex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    return emailRegex.match(email)

def validatePassword(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def hashPassword(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def checkPassword(password, hashedPassword):
    return bcrypt.checkpw(password.encode('utf-8'), hashedPassword)

def loadUsers():
    users = {}
    try:
        with open(userCsv, 'r') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                print(f"Warning: The CSV file {userCsv} is empty or improperly formatted.")
                return users

            requiredFields = ['email', 'password', 'securityQuestion']
            if not set(requiredFields).issubset(reader.fieldnames):
                print(f"Error: CSV file is missing required columns. Expected: {', '.join(requiredFields)}")
                print(f"Found: {', '.join(reader.fieldnames)}")
                return users

            for row in reader:
                try:
                    users[row['email']] = {
                        'password': row['password'].encode('utf-8'),
                        'securityQuestion': row['securityQuestion']
                    }
                except KeyError as e:
                    print(f"Error: Missing data for user {row.get('email', 'unknown')}: {str(e)}")
    except FileNotFoundError:
        print(f"Warning: User file {userCsv} not found. Starting with an empty user database.")
    except csv.Error as e:
        print(f"Error reading CSV file: {str(e)}")
    return users

def saveUsers(users):
    with open(userCsv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'password', 'securityQuestion'])
        writer.writeheader()
        for email, data in users.items():
            writer.writerow({
                'email': email,
                'password': data['password'].decode('utf-8'),
                'securityQuestion': data['securityQuestion']
            })

def logAction(email, action):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(historyCsv, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([timestamp, email, action])

def createAccount(users):
    print("\nCreating a new account:")
    email = input("Enter your email: ")
    while not validateEmail(email):
        print("Invalid email format. Please try again.")
        email = input("Enter your email: ")

    if email in users:
        print("An account with this email already exists.")
        return

    password = getpass.getpass("Enter your password (hidden): ")
    while not validatePassword(password):
        print("Password must be at least 8 characters long and contain uppercase, lowercase, digit, and special character.")
        password = getpass.getpass("Enter your password (hidden): ")

    securityQuestion = input("Enter a security question for password recovery: ")

    users[email] = {
        'password': hashPassword(password),
        'securityQuestion': securityQuestion
    }
    saveUsers(users)
    logAction(email, "Account created")
    print("Account created successfully!")

def generateCaptcha():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def verifyCaptcha():
    captcha = generateCaptcha()
    print(f"CAPTCHA: {captcha}")
    userInput = input("Enter the CAPTCHA: ")
    return userInput.upper() == captcha

def login(users):
    attempts = 0
    while attempts < maxLoginAttempts:
        email = input("Enter your email: ")
        if email not in users:
            print("Email not found.")
            forgotChoice = input("Do you want to reset your password? (y/n): ")
            if forgotChoice.lower() == 'y':
                forgotPassword(users, email)
            continue

        password = getpass.getpass("Enter your password (hidden): ")

        if not verifyCaptcha():
            print("CAPTCHA verification failed. Please try again.")
            continue

        if checkPassword(password, users[email]['password']):
            print("Login successful!")
            logAction(email, "Successful login")
            return email
        else:
            attempts += 1
            remaining = maxLoginAttempts - attempts
            print(f"Invalid password. {remaining} attempts remaining.")
            logAction(email, "Failed login attempt")
            if remaining > 0:
                forgotChoice = input("Do you want to reset your password? (y/n): ")
                if forgotChoice.lower() == 'y':
                    forgotPassword(users, email)
                    return None

    print("Maximum login attempts exceeded. Exiting.")
    return None

def forgotPassword(users, email=None):
    if email is None:
        email = input("Enter your email: ")
    if email not in users:
        print("Email not found.")
        return

    securityAnswer = input(f"Security Question: {users[email]['securityQuestion']}\nYour answer: ")
    if securityAnswer.lower() == users[email]['securityQuestion'].lower():
        newPassword = getpass.getpass("Enter your new password (hidden): ")
        while not validatePassword(newPassword):
            print("Password must be at least 8 characters long and contain uppercase, lowercase, digit, and special character.")
            newPassword = getpass.getpass("Enter your new password (hidden): ")

        users[email]['password'] = hashPassword(newPassword)
        saveUsers(users)
        logAction(email, "Password reset")
        print("Password reset successful!")
    else:
        print("Incorrect answer to security question.")
        logAction(email, "Failed password reset attempt")

def getAstronomyData(location):
    url = f"https://api.ipgeolocation.io/astronomy?apiKey={apiKey}&location={location}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None

def parseTime(timeStr):
    return datetime.strptime(timeStr, "%H:%M").time()

def displayAstronomyData(data):
    if data:
        try:
            date = datetime.strptime(data['date'], "%Y-%m-%d").date()
            currentTime = datetime.strptime(data['current_time'].split('.')[0], "%H:%M:%S").time()
            sunrise = parseTime(data['sunrise'])
            sunset = parseTime(data['sunset'])
            solarNoon = parseTime(data['solar_noon'])
            dayLength = timedelta(hours=int(data['day_length'][:2]), minutes=int(data['day_length'][3:5]))

            location = f"{data['location']['city']}, {data['location']['state']}, {data['location']['country']}"
            if not data['location']['city']:
                location = f"{data['location']['state']}, {data['location']['country']}"

            print(f"\nAstronomy data for {location}:")
            print(f"Date: {date}")
            print(f"Current Time: {currentTime}")
            print(f"Sunrise: {sunrise.strftime('%I:%M %p')}")
            print(f"Sunset: {sunset.strftime('%I:%M %p')}")
            print(f"Solar Noon: {solarNoon.strftime('%I:%M %p')}")
            print(f"Day Length: {dayLength}")
        except (KeyError, ValueError) as e:
            print(f"Error: Invalid data format in API response: {e}")
    else:
        print("Unable to retrieve astronomy data.")

def main():
    users = loadUsers()

    while True:
        print("\n1. Login")
        print("2. Create Account")
        print("3. Exit")
        choice = input("Enter your choice (1-3): ")

        if choice == '1':
            loggedInUser = login(users)
            if loggedInUser:
                while True:
                    print("\n1. Get Astronomy Data")
                    print("2. Logout")
                    loggedInChoice = input("Enter your choice (1-2): ")

                    if loggedInChoice == '1':
                        location = input("\nEnter a city or location: ")
                        astronomyData = getAstronomyData(location)
                        displayAstronomyData(astronomyData)
                        logAction(loggedInUser, f"Fetched astronomy data for {location}")
                    elif loggedInChoice == '2':
                        logAction(loggedInUser, "Logout")
                        break
                    else:
                        print("Invalid choice. Please try again.")
        elif choice == '2':
            createAccount(users)
        elif choice == '3':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()