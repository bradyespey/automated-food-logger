// static/js/script.js

async function submitFoodLog() {
    const logButton = document.querySelector('.nav-buttons button:nth-child(1)');
    const spinner = document.getElementById('spinner');
    const responseMessage = document.getElementById('response-message');
    const logText = document.getElementById('food-log-text').value;
    const logWaterToggle = document.getElementById('log-water-toggle') ? document.getElementById('log-water-toggle').checked : true;

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
        return;
    }

    try {
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
    const responseMessage = document.getElementById('response-message');
    if (responseMessage) {
        const text = responseMessage.innerText;
        navigator.clipboard.writeText(text).then(() => {
            const copyButton = document.querySelector('.nav-buttons button:nth-child(6)');
            if (copyButton) {
                copyButton.textContent = 'Copied!';
                setTimeout(() => {
                    copyButton.textContent = 'Copy Output';
                }, 2000);
            }
        });
    }
}

function showHydrationCalculator() {
    const foodLogSection = document.getElementById('food-log-section');
    const hydrationCalculatorSection = document.getElementById('hydration-calculator-section');
    if (foodLogSection && hydrationCalculatorSection) {
        foodLogSection.style.display = 'none';
        hydrationCalculatorSection.style.display = 'flex';
    }
}

function calculateHydration() {
    const hydrationTypeElement = document.getElementById('hydration-type');
    const hydrationAmountElement = document.getElementById('hydration-amount');
    const hydrationResult = document.getElementById('hydration-result');

    if (!hydrationTypeElement || !hydrationAmountElement || !hydrationResult) {
        return;
    }

    const hydrationType = parseFloat(hydrationTypeElement.value);
    const hydrationAmount = parseFloat(hydrationAmountElement.value);

    if (isNaN(hydrationAmount) || hydrationAmount <= 0) {
        hydrationResult.textContent = "Please enter a valid amount.";
        return;
    }

    const hydrationValue = hydrationType * hydrationAmount;
    hydrationResult.textContent = `Hydration Value: ${hydrationValue.toFixed(2)} fl oz`;
}

function openFoodvisor() {
    window.open('https://www.foodvisor.io/en/vision/#demo', '_blank');
}

async function loadExample() {
    try {
        const response = await fetch('/foodlog/example', { cache: 'no-store' });
        if (response.ok) {
            const text = await response.text();
            const foodLogText = document.getElementById('food-log-text');
            if (foodLogText) {
                foodLogText.value = text;
            }
        } else {
            alert("Failed to load example");
        }
    } catch (error) {
        alert("Error loading example: " + error.message);
    }
}
