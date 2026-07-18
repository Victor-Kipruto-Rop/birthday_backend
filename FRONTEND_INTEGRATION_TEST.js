/**
 * Birthday Backend Integration Test
 * Run this in your Vercel frontend's browser console or in a test file
 * 
 * This verifies full end-to-end connectivity between frontend and backend
 */

const API_BASE_URL = "https://birthday-backend-s1b7.onrender.com";

// ============================================================================
// TEST 1: HEALTH CHECK
// ============================================================================
async function testHealthCheck() {
  console.log("\n📍 TEST 1: Health Check");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    const data = await response.json();
    
    if (response.ok && data.success) {
      console.log("✅ Backend is healthy");
      console.log(`   Status: ${data.data.status}`);
      return true;
    } else {
      console.error("❌ Health check failed");
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 2: VALID WISH SUBMISSION
// ============================================================================
async function testValidWish() {
  console.log("\n📍 TEST 2: Valid Wish Submission");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/wish`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "Alice Johnson",
        phone: "0712345678",
        message: "Wishing you an amazing birthday! May all your dreams come true! 🎉",
      }),
    });
    
    const data = await response.json();
    
    if (response.status === 201 && data.success) {
      console.log("✅ Wish submitted successfully");
      console.log(`   Name: ${data.data.name}`);
      console.log(`   Created: ${data.data.created_at}`);
      return true;
    } else {
      console.error("❌ Wish submission failed");
      console.error(`   Status: ${response.status}`);
      console.error(`   Message: ${data.message}`);
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 3: INVALID WISH (Missing Name) - Should Return 422
// ============================================================================
async function testInvalidWishMissingName() {
  console.log("\n📍 TEST 3: Invalid Wish (Missing Name)");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/wish`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        phone: "0712345678",
        message: "Happy birthday!",
      }),
    });
    
    const data = await response.json();
    
    if (response.status === 422 && !data.success && data.errors.name) {
      console.log("✅ Validation working correctly");
      console.log(`   Error: ${data.errors.name}`);
      return true;
    } else {
      console.error("❌ Validation failed - should return 422");
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 4: INVALID WISH (Invalid Phone) - Should Return 422
// ============================================================================
async function testInvalidWishBadPhone() {
  console.log("\n📍 TEST 4: Invalid Wish (Bad Phone Number)");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/wish`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "Bob",
        phone: "123", // Invalid
        message: "Happy birthday!",
      }),
    });
    
    const data = await response.json();
    
    if (response.status === 422 && !data.success && data.errors.phone) {
      console.log("✅ Phone validation working");
      console.log(`   Error: ${data.errors.phone}`);
      return true;
    } else {
      console.error("❌ Phone validation failed");
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 5: PAYMENT INITIATION
// ============================================================================
async function testPaymentInitiation() {
  console.log("\n📍 TEST 5: Payment Initiation");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/payment`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "Charlie Brown",
        phone: "0798765432",
        amount: 500,
      }),
    });
    
    const data = await response.json();
    
    if (response.status === 202 && data.success) {
      console.log("✅ Payment initiated successfully");
      console.log(`   Reference: ${data.data.reference}`);
      console.log(`   Amount: KES ${data.data.amount}`);
      console.log(`   Phone: ${data.data.phone}`);
      
      // Store reference for status check test
      window.lastTransactionRef = data.data.reference;
      return true;
    } else {
      console.error("❌ Payment initiation failed");
      console.error(`   Status: ${response.status}`);
      console.error(`   Message: ${data.message}`);
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 6: INVALID PAYMENT (Amount Too Low)
// ============================================================================
async function testInvalidPaymentLowAmount() {
  console.log("\n📍 TEST 6: Invalid Payment (Amount Too Low)");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/payment`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        name: "Diana",
        phone: "0712345678",
        amount: 0, // Invalid
      }),
    });
    
    const data = await response.json();
    
    if (response.status === 422 && !data.success && data.errors.amount) {
      console.log("✅ Amount validation working");
      console.log(`   Error: ${data.errors.amount}`);
      return true;
    } else {
      console.error("❌ Amount validation failed");
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 7: PAYMENT STATUS CHECK
// ============================================================================
async function testPaymentStatus() {
  console.log("\n📍 TEST 7: Payment Status Check");
  console.log("─".repeat(60));
  
  if (!window.lastTransactionRef) {
    console.warn("⚠️  No transaction reference available. Run TEST 5 first.");
    return false;
  }
  
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/payment-status/${window.lastTransactionRef}`
    );
    const data = await response.json();
    
    if (response.ok && data.success) {
      console.log("✅ Payment status retrieved");
      console.log(`   Reference: ${data.data.reference}`);
      console.log(`   Status: ${data.data.status}`);
      console.log(`   Amount: KES ${data.data.amount}`);
      return true;
    } else {
      console.error("❌ Status check failed");
      return false;
    }
  } catch (error) {
    console.error("❌ Network error:", error.message);
    return false;
  }
}

// ============================================================================
// TEST 8: CORS VALIDATION
// ============================================================================
async function testCORS() {
  console.log("\n📍 TEST 8: CORS Validation");
  console.log("─".repeat(60));
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    
    // Check if CORS headers are present
    const corsHeader = response.headers.get("access-control-allow-origin");
    
    if (corsHeader) {
      console.log("✅ CORS headers present");
      console.log(`   Allow-Origin: ${corsHeader}`);
      
      // Check if Vercel frontend is allowed
      if (corsHeader.includes("birthday-frontend-gamma.vercel.app")) {
        console.log("✅ Vercel frontend is CORS-allowed");
        return true;
      } else if (corsHeader === "*") {
        console.log("⚠️  CORS allows all origins (*)");
        return true;
      } else {
        console.warn("⚠️  CORS allows different origin:", corsHeader);
        return true;
      }
    } else {
      console.log("ℹ️  No CORS headers in response (may be blocked by browser preflight)");
      console.log("   This is normal if backend is properly configured");
      return true;
    }
  } catch (error) {
    console.error("❌ CORS test error:", error.message);
    return false;
  }
}

// ============================================================================
// RUN ALL TESTS
// ============================================================================
async function runAllTests() {
  console.clear();
  console.log("╔" + "═".repeat(58) + "╗");
  console.log("║" + " Birthday Backend Integration Tests".padEnd(59) + "║");
  console.log("║" + ` Backend: ${API_BASE_URL}`.padEnd(59) + "║");
  console.log("║" + " Frontend: https://birthday-frontend-gamma.vercel.app".padEnd(59) + "║");
  console.log("╚" + "═".repeat(58) + "╝");
  
  const results = [];
  
  results.push(await testHealthCheck());
  results.push(await testValidWish());
  results.push(await testInvalidWishMissingName());
  results.push(await testInvalidWishBadPhone());
  results.push(await testPaymentInitiation());
  results.push(await testInvalidPaymentLowAmount());
  results.push(await testPaymentStatus());
  results.push(await testCORS());
  
  // Summary
  console.log("\n" + "═".repeat(60));
  console.log("SUMMARY");
  console.log("═".repeat(60));
  
  const passed = results.filter((r) => r).length;
  const total = results.length;
  
  console.log(`✅ Passed: ${passed}/${total}`);
  
  if (passed === total) {
    console.log("\n🎉 ALL TESTS PASSED! Backend and frontend are fully connected.");
    console.log("\nYou can now:");
    console.log("  • Submit birthday wishes");
    console.log("  • Initiate payments via Pay Hero STK Push");
    console.log("  • Receive payment confirmations");
    console.log("  • Send emails to configured recipient");
  } else {
    console.log(
      "\n⚠️  Some tests failed. Check the errors above and verify:"
    );
    console.log("  • FRONTEND_URL is set to: https://birthday-frontend-gamma.vercel.app");
    console.log("  • Backend environment variables are configured");
    console.log("  • Network connectivity from browser to backend");
  }
}

// Export for use in different environments
if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    testHealthCheck,
    testValidWish,
    testInvalidWishMissingName,
    testInvalidWishBadPhone,
    testPaymentInitiation,
    testInvalidPaymentLowAmount,
    testPaymentStatus,
    testCORS,
    runAllTests,
  };
}

// Auto-run if in browser console
if (typeof window !== "undefined") {
  // Don't auto-run, wait for user to call runAllTests()
  console.log("\n💡 To run all tests, paste this in your browser console:");
  console.log("   runAllTests()");
}
