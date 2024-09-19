# Food Logging Automation

## Overview

**FoodLoggingAutomation** is a Python-based project designed to streamline the process of logging food intake data into the [Lose It!](https://loseit.com) website using Selenium automation. This project also integrates a custom GPT, [Estimate Nutritional Info GPT](https://chatgpt.com/g/g-VJEAwPuc8-estimate-nutritional-info), allowing users to query nutritional information for a meal or food item. The user can copy the results from the GPT into the web app, which then automates logging the food into Lose It! using Selenium.

Additionally, the project includes a hydration impact calculator, based on the WaterMinder app, for tracking daily water intake and its impact.

This project integrates key technologies such as **Google OAuth 2.0** for secure user authentication and **Nginx** to handle HTTPS requests. By using Selenium, the script interacts with Lose It! to log food details, including nutrition data, meal information, and serving sizes.

### Why Use FoodLoggingAutomation?
- **Automated Food Logging with GPT**: Ask [Estimate Nutritional Info GPT](https://chatgpt.com/g/g-VJEAwPuc8-estimate-nutritional-info) about a meal's nutritional info and copy the results into the web app to log them in Lose It! automatically.
- **Secure Authentication**: Uses Google OAuth 2.0 to keep user data secure.
- **Accurate Data Validation**: Ensures that the logged data matches user input.
- **Seamless Integration**: The local Flask app serves as a user interface, while the backend handles the heavy lifting with Selenium and Nginx.
- **Hydration Impact Tracking**: Integrated calculator to track hydration, similar to the WaterMinder app.

---

## Key Features

- **Custom GPT Integration**: Allows users to query the GPT for nutritional info, which can be copied directly into the app to log meals in Lose It!.
- **Flask Web Application**: A clean and simple interface for entering food data and interacting with GPT results.
- **OAuth 2.0 Authentication**: Secure login using your Google account.
- **Hydration Calculator**: Track daily water intake and calculate hydration impact based on WaterMinder.
- **Data Validation**: Ensures the food data logged into Lose It! matches the input.
- **Nginx Reverse Proxy**: Enables secure HTTPS connections for the web interface.
- **Error Handling and Logging**: Extensive logging and debugging capabilities for easy troubleshooting.

---

## Screenshots

### Food Logging Interface
This is the main interface where users enter food data or paste nutritional info retrieved from GPT.

![Food Logging](images/food_logging.png)
![Food Example](images/food_example.png)

### Logged Food on Lose It!
After submitting food data, it automatically appears on your Lose It! account.

![Lose It!](images/lose_it.png)

---

## How It Works

1. **Query Nutritional Info via GPT**: Users can ask the [Estimate Nutritional Info GPT](https://chatgpt.com/g/g-VJEAwPuc8-estimate-nutritional-info) for details about a meal or food item. The GPT provides nutrition data like calories, macronutrients, and serving sizes.
2. **Copy Results to Web App**: Copy the results from GPT into the web app’s food logging interface.
3. **Automated Logging**: Selenium opens Lose It!, logs into your account (using stored cookies), and logs the food data automatically.
4. **Validation**: The system checks that the data logged into Lose It! matches what you input.
5. **Results**: A confirmation message is displayed once the food is logged, and you can see it live on Lose It!.
6. **Hydration Tracking**: Use the hydration calculator to track daily water intake and see its impact.

---

## Setup Instructions

Follow these steps to set up **FoodLoggingAutomation**.

### 1. Install Python on Windows 11 Machine

Download and install Python from [python.org](https://www.python.org/downloads/windows/) and ensure it's added to your system PATH.

### 2. Install Required Packages

Run the following command to install the necessary Python packages:

```bash
pip install flask requests selenium webdriver-manager cryptography pyopenssl gevent
```

### 3. Set Up the Project Directory

- **Main Directory**: `C:\Projects\LoseIt`
- **HTML Web Page**: `C:\Projects\LoseIt\index.html`
- **Scripts Folder**: `C:\Projects\LoseIt\Scripts`
  - `import_foods.py`
  - `loseit_cookies.json`
  - `save_cookies.json`
- **Static Folder**: `C:\Projects\LoseIt\Static`
  - **CSS**: `styles.css`
  - **JS**: `script.js`
  - **Images**: `loseit_icon.png`, `loseit_logo.png`

---

### 4. Set Up the Flask App

The Flask app is located at `C:\Projects\LoseIt\app.py`. It provides a secure interface for inputting food data, querying GPT for nutritional info, and logging data into the Lose It! website via Selenium automation.

To run the app, use:

```bash
python app.py
```

#### SSL Support

The app is configured to use SSL for secure connections. After generating the SSL certificates using Let's Encrypt, configure the Flask app to use the combined certificate.

To do this:

- Create the necessary directory structure:

  ```bash
  mkdir "C:\Projects\LoseIt\webroot"
  mkdir "C:\Projects\LoseIt\webroot\.well-known"
  mkdir "C:\Projects\LoseIt\webroot\.well-known\acme-challenge"
  ```

- Place a test file in the challenge directory:

  ```bash
  echo "Test" > "C:\Projects\LoseIt\webroot\.well-known\acme-challenge\test.txt"
  ```

- Generate the SSL certificates using the **win-acme** tool. Ensure they are saved to the `C:\Projects\certs\` directory.

- Update the Flask app to use the SSL certificates:

  ```python
  context = ('C:/Projects/certs/your-domain.com-fullchain.pem', 'C:/Projects/certs/your-domain.com-key-nopass.pem')
  app.run(ssl_context=context)
  ```

---

### 5. Configure Nginx

Nginx is used to reverse proxy incoming HTTP/HTTPS requests to the Flask app.

- Download and extract Nginx to `C:\Projects\Nginx`
- Update `C:\Projects\Nginx\conf\nginx.conf` with the following configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com www.your-domain.com;

    ssl_certificate "C:/Projects/certs/your-domain.com-fullchain.pem";
    ssl_certificate_key "C:/Projects/certs/your-domain.com-key-nopass.pem";

    location /foodlog {
        proxy_pass http://localhost:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- Start Nginx using the following command:

```bash
cd C:\Projects\Nginx
start nginx
```

- To reload the Nginx configuration after changes:

```bash
nginx.exe -s reload
```

---

### 6. Set Up OAuth 2.0 Authentication

Set up Google OAuth 2.0 to authenticate users for the Flask app.

- Go to the [Google Cloud Console](https://console.cloud.google.com/)
- Create a new project and configure OAuth consent screen with details such as:
  - **App name**: Lose It! Food Logging
  - **Authorized domain**: your-domain.com
  - **Redirect URI**: https://your-domain.com/foodlog/oauth2callback

- Add the OAuth credentials to `api_credentials.json` located in `C:\Projects\LoseIt\`:

```json
{
  "client_id": "YOUR_GOOGLE_CLIENT_ID",
  "client_secret": "YOUR_GOOGLE_CLIENT_SECRET",
  "redirect_uri": "https://your-domain.com/foodlog/oauth2callback"
}
```

Ensure this file is not included in the repository by adding it to `.gitignore`.

---

### 7. Automate Logging with Selenium

The food logging process is automated using Selenium WebDriver. The script `import_foods.py` is responsible for logging food data into the Lose It! website.

- The script:
  - Loads the Lose It! website using stored cookies for authentication.
  - Navigates to the correct date for food logging.
  - Enters food data such as name, quantity, calories, and other nutritional information.
  - Validates that the food is logged correctly.

To run the script manually, execute:

```bash
python C:\Projects\LoseIt\scripts\import_foods.py
```

---

### 8. Set Up NSSM for Service Management

Use NSSM to run Flask and Nginx as services that start automatically on boot.

- Download and extract NSSM to `C:\Projects\nss

m`
- Install the Flask app as a service:

```bash
nssm install FoodLogApp
```

Configure the service with the following settings:

- **Path**: `C:\Users\espey\AppData\Local\Programs\Python\Python312\python.exe`
- **Arguments**: `C:\Projects\GitHub\LoseIt\app.py`
- **Startup Directory**: `C:\Projects\GitHub\LoseIt`
- **Log Output**: `C:\Projects\LoseIt\logs\flask_stdout.log`
- **Log Error**: `C:\Projects\LoseIt\logs\flask_stderr.log`

To start the service:

```bash
nssm start FoodLogApp
```

Verify the service is running:

```bash
nssm status FoodLogApp
```

---

### 9. Testing

To test that everything is working correctly:

- Access the Flask app on your local network: [http://192.168.0.100/foodlog](http://192.168.0.100/foodlog)
- Access the app externally via your domain: [https://your-domain.com/foodlog](https://your-domain.com/foodlog)
- Use the OAuth 2.0 login, submit food data, and verify that it is logged into the "Lose It!" website.

---

## Troubleshooting & Logs

- Flask logs can be found at `C:\Projects\LoseIt\logs\flask_stdout.log` and `C:\Projects\LoseIt\logs\flask_stderr.log`.
- Nginx logs are stored at `C:\Projects\Nginx\logs`.