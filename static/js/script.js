// static/js/script.js

document.addEventListener('DOMContentLoaded', () => {
    // Read the login state from the body's data attribute.
    const bodyEl = document.querySelector('body');
    const loggedInAttr = bodyEl.getAttribute('data-loggedin'); // "true" or "false"
    const loggedIn = (loggedInAttr === 'true');
  
    // Get DOM elements.
    const logFoodButton = document.getElementById('log-food-button');
    const clearButton = document.getElementById('clear-button');
    const exampleButton = document.getElementById('example-button');
    const foodvisorButton = document.getElementById('foodvisor-button');
    const hydrationCalculatorButton = document.getElementById('hydration-calculator-button');
    const calculateHydrationButton = document.getElementById('calculate-hydration-button');
    const copyOutputButton = document.getElementById('copy-output-button');
    const authButton = document.getElementById('auth-button');
    const logWaterToggle = document.getElementById('log-water-toggle');
  
    // Persist the Log Water toggle state via localStorage.
    if (logWaterToggle) {
      const storedValue = localStorage.getItem('logWaterToggle');
      if (storedValue !== null) {
        logWaterToggle.checked = (storedValue === 'true');
      }
      logWaterToggle.addEventListener('change', () => {
        localStorage.setItem('logWaterToggle', logWaterToggle.checked);
      });
    }
  
    // Attach event listener to the auth (Login/Logout) button.
    if (authButton) {
      authButton.addEventListener('click', () => {
        // If logged in, go to logout; if not, go to login.
        if (loggedIn) {
          window.location.href = '/foodlog/logout';
        } else {
          window.location.href = '/foodlog/login';
        }
      });
    }
  
    // Attach event listener to the Log Food button.
    if (logFoodButton) {
      logFoodButton.addEventListener('click', () => {
        if (!loggedIn) {
          alert("Please log in to log food.");
          return;
        }
        submitFoodLog();
      });
    }
  
    // Attach other event listeners.
    if (clearButton) {
      clearButton.addEventListener('click', clearLog);
    }
    if (exampleButton) {
      exampleButton.addEventListener('click', loadExample);
    }
    if (foodvisorButton) {
      foodvisorButton.addEventListener('click', openFoodvisor);
    }
    if (hydrationCalculatorButton) {
      hydrationCalculatorButton.addEventListener('click', showHydrationCalculator);
    }
    if (calculateHydrationButton) {
      calculateHydrationButton.addEventListener('click', calculateHydration);
    }
    if (copyOutputButton) {
      copyOutputButton.addEventListener('click', copyOutput);
    }
  });
  
  // Function to submit a food log.
  async function submitFoodLog() {
    console.log("submitFoodLog called");
    const logFoodButton = document.getElementById('log-food-button');
    const spinner = document.getElementById('spinner');
    const responseMessage = document.getElementById('response-message');
    const logText = document.getElementById('food-log-text').value;
    const logWaterToggleValue = document.getElementById('log-water-toggle')
      ? document.getElementById('log-water-toggle').checked
      : true;
  
    if (logFoodButton) {
      logFoodButton.textContent = 'Logging...';
      logFoodButton.disabled = true;
    }
    if (spinner) {
      spinner.style.display = 'inline-block';
    }
    if (responseMessage) {
      responseMessage.innerHTML = '';
    }
  
    if (!logText.trim()) {
      if (responseMessage) {
        responseMessage.innerHTML = '<span style="color: red;">Please enter your food log.</span>';
      }
      if (logFoodButton) {
        logFoodButton.textContent = 'Log Food';
        logFoodButton.disabled = false;
      }
      if (spinner) {
        spinner.style.display = 'none';
      }
      console.log("No log text entered");
      return;
    }
  
    try {
      console.log("Submitting food log...");
      const response = await fetch('/foodlog/submit-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        cache: 'no-store',
        body: JSON.stringify({ log: logText, log_water: logWaterToggleValue })
      });
  
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const data = await response.json();
        if (data.output) {
          if (responseMessage) {
            responseMessage.innerHTML = data.output;
          }
          console.log("Food log processed successfully.");
        } else {
          if (responseMessage) {
            responseMessage.innerHTML = '<span style="color: red;">Unexpected response from server.</span>';
          }
        }
      } else {
        const errorText = await response.text();
        if (responseMessage) {
          responseMessage.innerHTML = `<span style="color: red;">Error: ${errorText}</span>`;
        }
      }
    } catch (error) {
      console.error("Error in submitFoodLog:", error);
      if (responseMessage) {
        responseMessage.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
      }
    } finally {
      if (logFoodButton) {
        logFoodButton.textContent = 'Log Food';
        logFoodButton.disabled = false;
      }
      if (spinner) {
        spinner.style.display = 'none';
      }
    }
  }
  
  // Function to clear the food log text and response.
  function clearLog() {
    console.log("clearLog called");
    const foodLogText = document.getElementById("food-log-text");
    if (foodLogText) {
      foodLogText.value = "";
    }
    const responseMessage = document.getElementById("response-message");
    if (responseMessage) {
      responseMessage.innerHTML = "";
    }
  }
  
  // Function to copy the output to the clipboard.
  function copyOutput() {
    console.log("copyOutput called");
    const responseMessage = document.getElementById('response-message');
    if (responseMessage) {
      const text = responseMessage.innerText;
      navigator.clipboard.writeText(text).then(() => {
        console.log("Copied to clipboard");
        const copyButton = document.getElementById('copy-output-button');
        if (copyButton) {
          copyButton.textContent = 'Copied!';
          setTimeout(() => {
            copyButton.textContent = 'Copy Output';
          }, 2000);
        }
      }).catch(err => {
        console.error("Error copying text: ", err);
      });
    }
  }
  
  // Function to show the hydration calculator.
  function showHydrationCalculator() {
    console.log("showHydrationCalculator called");
    const foodLogSection = document.getElementById('food-log-section');
    const hydrationCalculatorSection = document.getElementById('hydration-calculator-section');
    if (foodLogSection && hydrationCalculatorSection) {
      foodLogSection.style.display = 'none';
      hydrationCalculatorSection.style.display = 'flex';
    }
  }
  
  // Function to calculate hydration.
  function calculateHydration() {
    console.log("calculateHydration called");
    const hydrationTypeElement = document.getElementById('hydration-type');
    const hydrationAmountElement = document.getElementById('hydration-amount');
    const hydrationResult = document.getElementById('hydration-result');
  
    if (!hydrationTypeElement || !hydrationAmountElement || !hydrationResult) {
      console.warn("Hydration elements not found");
      return;
    }
  
    const hydrationType = parseFloat(hydrationTypeElement.value);
    const hydrationAmount = parseFloat(hydrationAmountElement.value);
  
    if (isNaN(hydrationAmount) || hydrationAmount <= 0) {
      hydrationResult.textContent = "Please enter a valid amount.";
      console.log("Invalid hydration amount entered");
      return;
    }
  
    const hydrationValue = hydrationType * hydrationAmount;
    hydrationResult.textContent = `Hydration Value: ${hydrationValue.toFixed(2)} fl oz`;
  }
  
  // Function to open Foodvisor in a new tab.
  function openFoodvisor() {
    console.log("openFoodvisor called");
    window.open('https://www.foodvisor.io/en/vision/#demo', '_blank');
  }
  
  // Function to load an example food log.
  async function loadExample() {
    console.log("loadExample called");
    try {
      const response = await fetch('/foodlog/example', { cache: 'no-store' });
      if (response.ok) {
        const text = await response.text();
        const foodLogText = document.getElementById('food-log-text');
        if (foodLogText) {
          foodLogText.value = text;
        }
        console.log("Example loaded successfully");
      } else {
        alert("Failed to load example");
        console.error("Failed to load example:", response.statusText);
      }
    } catch (error) {
      alert("Error loading example: " + error.message);
      console.error("Error loading example:", error);
    }
  }
  