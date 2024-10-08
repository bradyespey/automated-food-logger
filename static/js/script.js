async function submitFoodLog() {
    const logButton = document.querySelector('.nav-buttons button:nth-child(1)');
    logButton.textContent = 'Logging...';
    const responseMessage = document.getElementById('response-message');
    responseMessage.innerHTML = '';  // Clear previous output
    const logText = document.getElementById('food-log-text').value;

    try {
        const response = await fetch('/foodlog/submit-log', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ log: logText })
        });

        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            const result = await response.json();
            responseMessage.innerHTML = result.output;
        } else {
            const errorText = await response.text();
            responseMessage.innerHTML = `<span style="color: red;">Error: Received unexpected response: ${errorText}</span>`;
        }
    } catch (error) {
        responseMessage.innerHTML = `<span style="color: red;">Error: ${error.message}</span>`;
    } finally {
        logButton.textContent = 'Log Food';
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
        const copyButton = document.querySelector('.nav-buttons button:nth-child(4)');
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

// Function to open the Foodvisor link
function openFoodvisor() {
    window.open('https://www.foodvisor.io/en/vision/#demo', '_blank');
}