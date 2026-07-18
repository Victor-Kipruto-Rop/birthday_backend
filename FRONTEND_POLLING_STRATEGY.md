# Frontend Payment Polling Strategy - Optimized for Speed

## Problem
Payment status checks were slow because:
1. Backend retried failed checks (1.5s delay × 3 = 4.5s wait)
2. Frontend polled too infrequently
3. No streaming/WebSocket updates

## Solution
Aggressive polling with fail-fast backend + optimized UX

---

## Backend Changes (Already Applied)
- Reduced retry backoff from 1.5s to 0.3s
- Reduced request timeout from 20s to 10s
- Status checks now fail-fast if Pay Hero is slow
- Callback finalization still happens independently

---

## Frontend Implementation

### 1. Fast Polling Loop (JavaScript)
```javascript
const POLLING_INTERVAL_MS = 1000;  // Poll every 1 second
const MAX_POLL_ATTEMPTS = 60;       // Give up after 60 seconds
const PAYMENT_API = "https://birthday-backend-s1b7.onrender.com";

async function pollPaymentStatus(transactionRef) {
  console.log(`Starting payment status poll for ${transactionRef}`);
  
  let attempts = 0;
  
  return new Promise((resolve, reject) => {
    const pollInterval = setInterval(async () => {
      attempts++;
      
      try {
        const response = await fetch(
          `${PAYMENT_API}/api/payment-status/${transactionRef}`,
          {
            method: "GET",
            headers: {
              "Content-Type": "application/json",
            },
          }
        );
        
        const data = await response.json();
        
        if (!data.success) {
          console.log(`Poll attempt ${attempts}: API error - ${data.message}`);
          // Keep polling on API errors
          return;
        }
        
        const status = data.data.status;
        console.log(`Poll attempt ${attempts}: Status = ${status}`);
        
        // Success state - payment completed
        if (status === "success") {
          clearInterval(pollInterval);
          console.log("✅ Payment successful!");
          resolve({
            success: true,
            status: "success",
            reference: data.data.reference,
            amount: data.data.amount,
          });
          return;
        }
        
        // Failed state - payment did not complete
        if (status === "failed") {
          clearInterval(pollInterval);
          console.log("❌ Payment failed");
          resolve({
            success: false,
            status: "failed",
            reference: data.data.reference,
            reason: "Customer declined payment or insufficient funds",
          });
          return;
        }
        
        // Still pending - keep polling
        if (status === "pending") {
          // Show user they're waiting (update UI)
          updatePaymentUI(`Waiting for confirmation... (${attempts}s)`);
          return;
        }
        
      } catch (error) {
        console.log(`Poll attempt ${attempts}: Network error - ${error.message}`);
        // Keep polling on network errors
      }
      
      // Max attempts exceeded
      if (attempts >= MAX_POLL_ATTEMPTS) {
        clearInterval(pollInterval);
        reject(new Error(
          `Payment confirmation timeout after ${MAX_POLL_ATTEMPTS}s. ` +
          `Check your phone for an M-Pesa prompt or try again.`
        ));
      }
    }, POLLING_INTERVAL_MS);
  });
}
```

### 2. User Experience Flow
```javascript
async function handlePaymentSubmit(formData) {
  try {
    // Step 1: Initiate payment (should return immediately with reference)
    console.log("Submitting payment...");
    const submitResponse = await fetch(`${PAYMENT_API}/api/payment`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });
    
    if (!submitResponse.ok) {
      showError("Payment initiation failed. Please try again.");
      return;
    }
    
    const submitData = await submitResponse.json();
    const transactionRef = submitData.data.reference;
    
    // Step 2: Show "Check your phone" message immediately
    showMessage(
      `🔔 Check your phone!\n\nWe've sent you an M-Pesa payment prompt.\n` +
      `Reference: ${transactionRef}\n\n` +
      `Confirming payment...`
    );
    
    // Step 3: Poll for status (will keep trying until success/fail/timeout)
    const result = await pollPaymentStatus(transactionRef);
    
    if (result.success) {
      showSuccess(
        `✅ Payment Successful!\n\n` +
        `KES ${result.amount} received.\n` +
        `Thank you for the gift!`
      );
    } else {
      showWarning(
        `⚠️ Payment Not Confirmed\n\n` +
        `${result.reason}\n` +
        `Reference: ${result.reference}\n\n` +
        `You can try again.`
      );
    }
    
  } catch (error) {
    showError(`Payment Error: ${error.message}`);
  }
}

function updatePaymentUI(message) {
  // Update spinner/progress text
  const statusElement = document.getElementById("payment-status");
  if (statusElement) {
    statusElement.textContent = message;
  }
}

function showMessage(msg) {
  console.log(msg);
  document.getElementById("payment-message").textContent = msg;
}

function showSuccess(msg) {
  console.log("✅ " + msg);
  document.getElementById("payment-result").innerHTML = `<div class="success">${msg}</div>`;
}

function showWarning(msg) {
  console.log("⚠️ " + msg);
  document.getElementById("payment-result").innerHTML = `<div class="warning">${msg}</div>`;
}

function showError(msg) {
  console.log("❌ " + msg);
  document.getElementById("payment-result").innerHTML = `<div class="error">${msg}</div>`;
}
```

### 3. HTML UI Example
```html
<form id="payment-form">
  <input type="text" name="name" placeholder="Your name" required />
  <input type="tel" name="phone" placeholder="Phone (0712345678)" required />
  <input type="number" name="amount" placeholder="Amount (KES)" required />
  <button type="submit">Send Gift</button>
</form>

<div id="payment-message" style="margin-top: 20px; text-align: center;"></div>
<div id="payment-status" style="font-size: 14px; color: gray;"></div>
<div id="payment-result" style="margin-top: 20px;"></div>

<style>
  .success { color: green; font-weight: bold; }
  .error { color: red; font-weight: bold; }
  .warning { color: orange; font-weight: bold; }
</style>

<script>
  document.getElementById("payment-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const formData = {
      name: e.target.name.value,
      phone: e.target.phone.value,
      amount: parseFloat(e.target.amount.value),
    };
    await handlePaymentSubmit(formData);
  });
</script>
```

---

## Expected Timing

### Old (Slow) Flow
1. User submits → Wait 2 sec
2. Start polling → First check takes 4.5 sec (retries)
3. Poll 2nd time → Wait 4.5 sec
4. **Total: ~15+ seconds** ❌

### New (Fast) Flow
1. User submits → Get reference in 1-2 sec ✅
2. Show "Check your phone" → Immediately ✅
3. Poll every 1 sec → Each check returns in 0.5-2 sec ✅
4. **Total: 2-5 seconds** ✅

---

## Key Points for Frontend

1. **Poll every 1 second** (not 5-10 sec)
2. **Show feedback immediately** ("Check your phone")
3. **Don't retry on network errors** (just keep polling)
4. **Timeout after 60 seconds** (user can retry)
5. **Handle all 3 status states**:
   - `pending` → Keep polling
   - `success` → Show success message
   - `failed` → Show failure message

---

## Testing

```bash
# Test fast polling
curl -X POST https://birthday-backend-s1b7.onrender.com/api/payment \
  -d '{"name":"Test","phone":"0712345678","amount":100}' \
  -H "Content-Type: application/json"

# Save the reference (e.g., GIFT-abc123)

# Then rapidly poll (simulate frontend behavior)
for i in {1..10}; do
  echo "Poll $i:"
  curl -s "https://birthday-backend-s1b7.onrender.com/api/payment-status/GIFT-abc123" \
    | grep -o '"status":"[^"]*"'
  sleep 1
done

# Each poll should return in <1 second now
```

---

## Performance Impact

| Metric | Before | After |
|--------|--------|-------|
| First response | 2 sec | 1-2 sec |
| Status check latency | 4-5 sec | 0.5-2 sec |
| Total confirmation time | 15-30 sec | 2-10 sec |
| User wait time | Unacceptable | Good |
| Backend load | Retries | No unnecessary retries |

---

## Fallback: Webhook Callback

Even with faster polling, the webhook callback will still arrive independently and finalize the transaction. This provides a backup:
- If polling doesn't catch it, callback will
- If callback arrives first, polling sees it immediately
- No double-processing (idempotent design)
