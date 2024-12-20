// static/js/script.js

async function submitFoodLog() {
    const logButton = document.querySelector('.nav-buttons button:nth-child(1)');
    const spinner = document.getElementById('spinner');
    logButton.textContent = 'Logging...';
    spinner.style.display = 'inline-block'; // Show spinner
    const responseMessage = document.getElementById('response-message');
    responseMessage.innerHTML = '';
    const logText = document.getElementById('food-log-text').value;
    
    // Get the state of the Log Water toggle
    const logWaterToggle = document.getElementById('log-water-toggle').checked;

    if (!logText.trim()) {
        responseMessage.innerHTML = '<span style="color: red;">Please enter your food log.</span>';
        logButton.textContent = 'Log Food';
        spinner.style.display = 'none';
        return;
    }

    try {
        const response = await fetch('/foodlog/submit-log', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ log: logText, log_water: logWaterToggle })
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            const data = await response.json();
            if (data.output) {
                responseMessage.innerHTML = data.output;

                // After successful logging, save the current text back to the file
                await fetch('/foodlog/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ log: logText })
                });
            } else {
                responseMessage.innerHTML = '<span style="color: red;">Unexpected response from server.</span>';
            }
        } else {
            const errorText = await response.text();
            responseMessage.innerHTML = `<span style="color: red;">Error: Received unexpected response: ${errorText}</span>`;
        }
    } catch (error) {
        responseMessage.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
    } finally {
        logButton.textContent = 'Log Food';
        spinner.style.display = 'none';
    }
}

function clearLog() {
    document.getElementById("food-log-text").value = "";
    document.getElementById("response-message").innerHTML = "";
}

function copyOutput() {
    const responseMessage = document.getElementById('response-message');
    const text = responseMessage.innerText;
    navigator.clipboard.writeText(text).then(() => {
        const copyButton = document.querySelector('.nav-buttons button:nth-child(6)');
        copyButton.textContent = 'Copied!';
        setTimeout(() => {
            copyButton.textContent = 'Copy Output';
        }, 2000);
    });
}

function showHydrationCalculator() {
    document.getElementById('food-log-section').style.display = 'none';
    document.getElementById('hydration-calculator-section').style.display = 'flex';
}

function calculateHydration() {
    const hydrationType = parseFloat(document.getElementById('hydration-type').value);
    const hydrationAmount = parseFloat(document.getElementById('hydration-amount').value);

    if (isNaN(hydrationAmount) || hydrationAmount <= 0) {
        document.getElementById('hydration-result').textContent = "Please enter a valid amount.";
        return;
    }

    const hydrationValue = hydrationType * hydrationAmount;
    document.getElementById('hydration-result').textContent = `Hydration Value: ${hydrationValue.toFixed(2)} fl oz`;
}

function openFoodvisor() {
    window.open('https://www.foodvisor.io/en/vision/#demo', '_blank');
}

async function loadExample() {
    try {
        const response = await fetch('/foodlog/example');
        if (response.ok) {
            const text = await response.text();
            document.getElementById('food-log-text').value = text;
        } else {
            alert("Failed to load example");
        }
    } catch (error) {
        alert("Error loading example: " + error.message);
    }
}
