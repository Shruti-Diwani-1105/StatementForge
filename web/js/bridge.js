// StatementForge Web Bridge Initialization
var pybridge = null;

function initWebBridge() {
    if (typeof qt !== "undefined" && typeof qt.webChannelTransport !== "undefined") {
        new QWebChannel(qt.webChannelTransport, function(channel) {
            pybridge = channel.objects.pybridge;
            console.log("PyQt WebBridge connected successfully.");
            window.dispatchEvent(new CustomEvent("pybridgeReady"));
        });
    } else {
        setTimeout(initWebBridge, 100);
    }
}

if (document.readyState === "complete" || document.readyState === "interactive") {
    initWebBridge();
} else {
    document.addEventListener("DOMContentLoaded", initWebBridge);
}

function sendAppCommand(action, payload) {
    var cmdStr = "app-cmd:" + action;
    if (payload !== undefined && payload !== null) {
        cmdStr += ":" + (typeof payload === "object" ? JSON.stringify(payload) : payload);
    }
    // Update document title - triggers Qt titleChanged signal instantly in Python
    document.title = cmdStr;
    // Reset title shortly after so consecutive clicks of the same command trigger titleChanged
    setTimeout(function() {
        document.title = "StatementForge";
    }, 10);
}

// Helper functions for UI actions
function navigateTo(pageName) {
    if (pybridge && typeof pybridge.navigateTo === "function") {
        try { pybridge.navigateTo(pageName); } catch(e) {}
    }
    sendAppCommand("navigate", pageName);
}

function submitLogin(email, password, remember) {
    if (pybridge && typeof pybridge.login === "function") {
        try { pybridge.login(email, password, remember); } catch(e) {}
    }
    sendAppCommand("login_submit", { email: email, password: password, remember: remember });
}

function submitRegister(fullName, email, password, confirmPassword) {
    if (pybridge && typeof pybridge.register === "function") {
        try { pybridge.register(fullName, email, password, confirmPassword); } catch(e) {}
    }
    sendAppCommand("register_submit", { fullName: fullName, email: email, password: password, confirmPassword: confirmPassword });
}

function triggerGoogleAuth() {
    if (pybridge && typeof pybridge.googleAuth === "function") {
        try { pybridge.googleAuth(); } catch(e) {}
    }
    sendAppCommand("google_auth");
}

function triggerForgotPassword() {
    if (pybridge && typeof pybridge.forgotPassword === "function") {
        try { pybridge.forgotPassword(); } catch(e) {}
    }
    sendAppCommand("forgot_password");
}
