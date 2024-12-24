// static/js/script.js

// Ensure the DOM is fully loaded before attaching event listeners
document.addEventListener('DOMContentLoaded', () => {
    // Select buttons by their unique IDs
    const logFoodButton = document.getElementById('log-food-button');
    const clearButton = document.getElementById('clear-button');
    const exampleButton = document.getElementById('example-button');
    const foodvisorButton = document.getElementById('foodvisor-button');
    const hydrationCalculatorButton = document.getElementById('hydration-calculator-button');
    const calculateHydrationButton = document.getElementById('calculate-hydration-button');
    const copyOutputButton = document.getElementById('copy-output-button');
    const logoutButton = document.getElementById('logout-button');

    // Attach event listeners if the elements exist
    if (logFoodButton) {
        logFoodButton.addEventListener('click', submitFoodLog);
    }

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

    if (logoutButton) {
        logoutButton.addEventListener('click', logoutUser);
    }
});

async function submitFoodLog() {
    console.log("submitFoodLog called");
    const logButton = document.getElementById('log-food-button');
    const spinner = document.getElementById('spinner');
    const responseMessage = document.getElementById('response-message');
    const logText = document.getElementById('food-log-text').value;
    const logWaterToggle = document.getElementById('log-water-toggle') 
        ? document.getElementById('log-water-toggle').checked 
        : true;

    if (logButton) {
        logButton.textContent = 'Logging...';
        logButton.disabled = true;
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
        if (logButton) {
            logButton.textContent = 'Log Food';
            logButton.disabled = false;
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
            body: JSON.stringify({ log: logText, log_water: logWaterToggle })
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            const data = await response.json();
            if (data.output) {
                if (responseMessage) {
                    responseMessage.innerHTML = data.output;
                }

                console.log("Saving log...");
                await fetch('/foodlog/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    cache: 'no-store',
                    body: JSON.stringify({ log: logText })
                });
            } else {
                if (responseMessage) {
                    responseMessage.innerHTML = '<span style="color: red;">Unexpected response from server.</span>';
                }
            }
        } else {
            const errorText = await response.text();
            if (responseMessage) {
                responseMessage.innerHTML = `<span style="color: red;">Error: Received unexpected response: ${errorText}</span>`;
            }
        }
    } catch (error) {
        console.error("Error in submitFoodLog:", error);
        if (responseMessage) {
            responseMessage.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
        }
    } finally {
        if (logButton) {
            logButton.textContent = 'Log Food';
            logButton.disabled = false;
        }
        if (spinner) {
            spinner.style.display = 'none';
        }
    }
}

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

function showHydrationCalculator() {
    console.log("showHydrationCalculator called");
    const foodLogSection = document.getElementById('food-log-section');
    const hydrationCalculatorSection = document.getElementById('hydration-calculator-section');
    if (foodLogSection && hydrationCalculatorSection) {
        foodLogSection.style.display = 'none';
        hydrationCalculatorSection.style.display = 'flex';
    }
}

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

function openFoodvisor() {
    console.log("openFoodvisor called");
    window.open('https://www.foodvisor.io/en/vision/#demo', '_blank');
}

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

// NEW: Logout user
function logoutUser() {
    console.log("logoutUser called");
    // This simply navigates to /foodlog/logout
    // which will clear the session and redirect back to the login screen
    window.location.href = '/foodlog/logout';
}
