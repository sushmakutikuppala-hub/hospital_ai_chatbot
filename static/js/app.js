/**
 * CareWell Hospital AI Receptionist & Clinical Portal - Frontend Logic
 * Strictly Protected Behind Mandatory Gmail Login
 */

document.addEventListener("DOMContentLoaded", () => {
  // Screens
  const authGate = document.getElementById("authGate");
  const appMain = document.getElementById("appMain");

  // Auth Elements
  const tabLoginBtn = document.getElementById("tabLoginBtn");
  const tabRegisterBtn = document.getElementById("tabRegisterBtn");
  const loginForm = document.getElementById("loginForm");
  const registerForm = document.getElementById("registerForm");
  const authAlert = document.getElementById("authAlert");

  // Logged-in Header Elements
  const userNameDisplay = document.getElementById("userNameDisplay");
  const welcomeGreeting = document.getElementById("welcomeGreeting");
  const logoutBtn = document.getElementById("logoutBtn");
  const myReportsBtn = document.getElementById("myReportsBtn");

  // Chat Elements
  const chatViewport = document.getElementById("chatViewport");
  const chatInput = document.getElementById("chatInput");
  const sendBtn = document.getElementById("sendBtn");
  const voiceBtn = document.getElementById("voiceBtn");
  const micIcon = document.getElementById("micIcon");
  const attachFileBtn = document.getElementById("attachFileBtn");
  const chipUploadReport = document.getElementById("chipUploadReport");

  // Modals
  const openReportModalBtn = document.getElementById("openReportModalBtn");
  const reportModal = document.getElementById("reportModal");
  const reportDropzone = document.getElementById("reportDropzone");
  const reportFileInput = document.getElementById("reportFileInput");
  const selectedFileLabel = document.getElementById("selectedFileLabel");
  const startAnalyzeBtn = document.getElementById("startAnalyzeBtn");
  const reportLoadingIndicator = document.getElementById("reportLoadingIndicator");
  const reportAnalysisResult = document.getElementById("reportAnalysisResult");

  const myReportsModal = document.getElementById("myReportsModal");
  const reportsHistoryList = document.getElementById("reportsHistoryList");

  const emergencyBtn = document.getElementById("emergencyBtn");
  const emergencyModal = document.getElementById("emergencyModal");
  const doctorsDirBtn = document.getElementById("doctorsDirBtn");
  const doctorsModal = document.getElementById("doctorsModal");
  const modalDoctorsList = document.getElementById("modalDoctorsList");
  const docSearchInput = document.getElementById("docSearchInput");

  const bookApptModalBtn = document.getElementById("bookApptModalBtn");
  const appointmentModal = document.getElementById("appointmentModal");
  const appointmentForm = document.getElementById("appointmentForm");
  const apptDoctorSelect = document.getElementById("apptDoctorSelect");
  const apptSuccessMessage = document.getElementById("apptSuccessMessage");

  // State
  const sessionId = "sess_" + Math.random().toString(36).substring(2, 11);
  let allDoctorsCache = [];
  let currentUser = JSON.parse(localStorage.getItem("carewell_user") || "null");
  let authToken = localStorage.getItem("carewell_token") || null;
  let selectedReportFile = null;

  // Initialize screen state: Check if already logged in with valid token
  initScreenGate();

  async function initScreenGate() {
    if (currentUser && authToken) {
      // Validate token with backend
      try {
        const res = await fetch("/api/auth/me", {
          headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (res.ok) {
          showAppScreen();
          return;
        }
      } catch (e) {
        // Network or token issue
      }
    }
    // Default: Must login first
    showAuthGate();
  }

  function showAuthGate() {
    authGate.style.display = "flex";
    appMain.style.display = "none";
    lucide.createIcons();
  }

  function showAppScreen() {
    authGate.style.display = "none";
    appMain.style.display = "flex";
    
    // Update profile in header
    const displayName = currentUser.full_name || currentUser.email.split('@')[0];
    userNameDisplay.textContent = displayName;
    welcomeGreeting.textContent = `Namaste, ${displayName}! I am Aura`;

    lucide.createIcons();
    loadDoctorsDirectory();
  }

  // ----------------- Auth Forms (Gmail Only) ----------------- //

  tabLoginBtn.addEventListener("click", () => {
    tabLoginBtn.classList.add("active");
    tabRegisterBtn.classList.remove("active");
    loginForm.style.display = "block";
    registerForm.style.display = "none";
    showAuthAlert("", "");
  });

  tabRegisterBtn.addEventListener("click", () => {
    tabRegisterBtn.classList.add("active");
    tabLoginBtn.classList.remove("active");
    registerForm.style.display = "block";
    loginForm.style.display = "none";
    showAuthAlert("", "");
  });

  function showAuthAlert(msg, type = "error") {
    if (!msg) {
      authAlert.style.display = "none";
      authAlert.textContent = "";
      return;
    }
    authAlert.style.display = "block";
    authAlert.className = `auth-alert ${type}`;
    authAlert.textContent = msg;
  }

  // Handle Login Submit
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    if (!email.toLowerCase().endsWith("@gmail.com")) {
      showAuthAlert("Invalid login: Only @gmail.com addresses are permitted (e.g. yourname@gmail.com).", "error");
      return;
    }

    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const data = await res.json();

      if (res.ok) {
        showAuthAlert("Login verified! Loading hospital portal...", "success");
        currentUser = data.user;
        authToken = data.token;
        localStorage.setItem("carewell_user", JSON.stringify(currentUser));
        localStorage.setItem("carewell_token", authToken);

        setTimeout(() => {
          loginForm.reset();
          showAppScreen();
        }, 800);
      } else {
        showAuthAlert(data.detail || "Login failed. Please verify your credentials.", "error");
      }
    } catch (err) {
      showAuthAlert("Connection error during login. Please try again.", "error");
    }
  });

  // Handle Register Submit
  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fullName = document.getElementById("regFullName").value.trim();
    const email = document.getElementById("regEmail").value.trim();
    const password = document.getElementById("regPassword").value;

    if (!email.toLowerCase().endsWith("@gmail.com")) {
      showAuthAlert("Registration domain error: Only @gmail.com addresses are allowed.", "error");
      return;
    }

    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, full_name: fullName })
      });
      const data = await res.json();

      if (res.ok) {
        showAuthAlert("Account created successfully with Gmail ID! Entering portal...", "success");
        currentUser = data.user;
        authToken = data.token;
        localStorage.setItem("carewell_user", JSON.stringify(currentUser));
        localStorage.setItem("carewell_token", authToken);

        setTimeout(() => {
          registerForm.reset();
          showAppScreen();
        }, 800);
      } else {
        showAuthAlert(data.detail || "Registration failed.", "error");
      }
    } catch (err) {
      showAuthAlert("Connection error during registration.", "error");
    }
  });

  // Logout Handler
  logoutBtn.addEventListener("click", () => {
    localStorage.removeItem("carewell_user");
    localStorage.removeItem("carewell_token");
    currentUser = null;
    authToken = null;
    showAuthGate();
    showAuthAlert("You have signed out. Please sign in again to access the hospital desk.", "success");
  });

  // ----------------- Speech Recognition ----------------- //

  let recognition = null;
  let isRecording = false;

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = "en-US";

    recognition.onstart = () => {
      isRecording = true;
      voiceBtn.classList.add("recording");
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      chatInput.value = transcript;
      handleSendMessage();
    };

    recognition.onerror = () => {
      isRecording = false;
      voiceBtn.classList.remove("recording");
    };

    recognition.onend = () => {
      isRecording = false;
      voiceBtn.classList.remove("recording");
    };
  } else {
    voiceBtn.style.display = "none";
  }

  // ----------------- Chat Stream Logic (Protected) ----------------- //

  async function handleSendMessage(overrideText = null) {
    const message = (overrideText || chatInput.value).trim();
    if (!message) return;

    if (!authToken) {
      alert("Authentication required. Please sign in with your @gmail.com account.");
      showAuthGate();
      return;
    }

    chatInput.value = "";
    appendUserMessage(message);
    scrollToBottom();

    const typingElem = showTypingIndicator();
    scrollToBottom();

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`
        },
        body: JSON.stringify({
          message: message,
          session_id: sessionId
        })
      });

      typingElem.remove();

      if (response.status === 401) {
        alert("Session expired. Please sign in again.");
        logoutBtn.click();
        return;
      }

      const data = await response.json();
      if (response.ok) {
        appendBotResponse(data);
      } else {
        appendBotMessage("I apologize, but I encountered an error connecting to our system. Please try again or call our reception desk directly.");
      }
    } catch (err) {
      typingElem.remove();
      appendBotMessage("I am currently experiencing connection difficulties. Please check your network or call our hospital desk at **+91-98765-43210**.");
    }

    scrollToBottom();
  }

  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
      <div class="message-bubble">${escapeHtml(text)}</div>
      <div class="message-avatar user-avatar">
        <i data-lucide="user" style="width:17px;height:17px;"></i>
      </div>
    `;
    chatViewport.appendChild(row);
    lucide.createIcons();
  }

  function appendBotResponse(data) {
    const row = document.createElement("div");
    row.className = "message-row bot";

    let formattedHtml = marked.parse(data.response || "");

    let doctorCardsHtml = "";
    if (data.matched_doctors && data.matched_doctors.length > 0) {
      doctorCardsHtml = `<div class="doctor-cards-grid">`;
      data.matched_doctors.forEach(doc => {
        doctorCardsHtml += `
          <div class="doctor-item-card">
            <div>
              <div class="doc-name">${escapeHtml(doc.name)}</div>
              <div class="doc-sub">${escapeHtml(doc.specialization)}</div>
              <div class="doc-detail">
                <i data-lucide="award" style="width:13px;height:13px;color:#0284c7;"></i>
                ${escapeHtml(doc.qualification)}
              </div>
              <div class="doc-detail">
                <i data-lucide="clock" style="width:13px;height:13px;color:#0284c7;"></i>
                ${escapeHtml(doc.timings)}
              </div>
              <div class="doc-detail">
                <i data-lucide="calendar" style="width:13px;height:13px;color:#0284c7;"></i>
                ${escapeHtml(doc.visiting_days)}
              </div>
              <div class="doc-detail">
                <i data-lucide="map-pin" style="width:13px;height:13px;color:#0284c7;"></i>
                ${escapeHtml(doc.room_no)} (${escapeHtml(doc.department_name)})
              </div>
            </div>
            <div class="doc-footer">
              <span class="doc-fee">Fee: ₹${doc.consultation_fee}</span>
              <button class="btn-book-sm" onclick="window.quickBookDoctor(${doc.id}, '${escapeHtml(doc.name)}')">
                Book OPD
              </button>
            </div>
          </div>
        `;
      });
      doctorCardsHtml += `</div>`;
    }

    const cleanTextToSpeak = (data.response || "").replace(/[#*`_\[\]()>-]/g, " ").replace(/\s+/g, " ");

    row.innerHTML = `
      <div class="message-avatar bot-avatar">
        <i data-lucide="bot" style="width:18px;height:18px;"></i>
      </div>
      <div class="message-bubble">
        ${formattedHtml}
        ${doctorCardsHtml}
        <div class="message-actions">
          <button class="msg-action-btn" onclick="window.speakReceptionistText(this)" data-text="${escapeHtml(cleanTextToSpeak)}">
            <i data-lucide="volume-2" style="width:13px;height:13px;"></i> Listen
          </button>
          <button class="msg-action-btn" onclick="window.copyMessageText(this)" data-copy="${escapeHtml(data.response)}">
            <i data-lucide="copy" style="width:13px;height:13px;"></i> Copy
          </button>
        </div>
      </div>
    `;

    chatViewport.appendChild(row);
    lucide.createIcons();
  }

  function appendBotMessage(plainText) {
    const row = document.createElement("div");
    row.className = "message-row bot";
    row.innerHTML = `
      <div class="message-avatar bot-avatar">
        <i data-lucide="bot" style="width:18px;height:18px;"></i>
      </div>
      <div class="message-bubble">
        ${marked.parse(plainText)}
      </div>
    `;
    chatViewport.appendChild(row);
    lucide.createIcons();
  }

  function showTypingIndicator() {
    const row = document.createElement("div");
    row.className = "message-row bot";
    row.id = "typingRow";
    row.innerHTML = `
      <div class="message-avatar bot-avatar">
        <i data-lucide="bot" style="width:18px;height:18px;"></i>
      </div>
      <div class="typing-indicator">
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
      </div>
    `;
    chatViewport.appendChild(row);
    lucide.createIcons();
    return row;
  }

  function scrollToBottom() {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }

  // ----------------- Text-to-Speech & Copy ----------------- //

  window.speakReceptionistText = function(btnElem) {
    if (!('speechSynthesis' in window)) {
      alert("Speech synthesis is not supported in this browser.");
      return;
    }
    window.speechSynthesis.cancel();
    const text = btnElem.getAttribute("data-text");
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    btnElem.style.color = "#0284c7";
    utterance.onend = () => {
      btnElem.style.color = "";
    };
    window.speechSynthesis.speak(utterance);
  };

  window.copyMessageText = function(btnElem) {
    const text = btnElem.getAttribute("data-copy");
    navigator.clipboard.writeText(text).then(() => {
      const orig = btnElem.innerHTML;
      btnElem.innerHTML = `<i data-lucide="check" style="width:13px;height:13px;"></i> Copied!`;
      lucide.createIcons();
      setTimeout(() => {
        btnElem.innerHTML = orig;
        lucide.createIcons();
      }, 2000);
    });
  };

  // ----------------- Medical Report Upload & Analysis ----------------- //

  function openReportModal() {
    reportModal.classList.add("active");
    selectedReportFile = null;
    selectedFileLabel.textContent = "";
    startAnalyzeBtn.disabled = true;
    reportAnalysisResult.style.display = "none";
    reportAnalysisResult.innerHTML = "";
    reportLoadingIndicator.style.display = "none";
    reportDropzone.style.display = "block";
  }

  if (openReportModalBtn) openReportModalBtn.addEventListener("click", openReportModal);
  if (attachFileBtn) attachFileBtn.addEventListener("click", openReportModal);
  if (chipUploadReport) chipUploadReport.addEventListener("click", openReportModal);

  reportDropzone.addEventListener("click", () => reportFileInput.click());

  reportDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    reportDropzone.classList.add("dragover");
  });

  reportDropzone.addEventListener("dragleave", () => {
    reportDropzone.classList.remove("dragover");
  });

  reportDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    reportDropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  reportFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelected(e.target.files[0]);
    }
  });

  function handleFileSelected(file) {
    selectedReportFile = file;
    selectedFileLabel.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    startAnalyzeBtn.disabled = false;
  }

  startAnalyzeBtn.addEventListener("click", async () => {
    if (!selectedReportFile) return;

    startAnalyzeBtn.disabled = true;
    reportLoadingIndicator.style.display = "block";
    reportAnalysisResult.style.display = "none";

    const formData = new FormData();
    formData.append("file", selectedReportFile);
    if (currentUser) {
      formData.append("user_email", currentUser.email);
    }

    try {
      const res = await fetch("/api/reports/upload", {
        method: "POST",
        headers: { "Authorization": `Bearer ${authToken}` },
        body: formData
      });

      reportLoadingIndicator.style.display = "none";

      if (res.status === 401) {
        alert("Session expired. Please sign in again.");
        logoutBtn.click();
        return;
      }

      const data = await res.json();
      if (res.ok) {
        renderReportAnalysis(data.analysis, selectedReportFile.name);
      } else {
        alert("Failed to analyze report: " + (data.detail || "Unknown error"));
        startAnalyzeBtn.disabled = false;
      }
    } catch (err) {
      reportLoadingIndicator.style.display = "none";
      alert("Error uploading and analyzing report. Please try again.");
      startAnalyzeBtn.disabled = false;
    }
  });

  function renderReportAnalysis(analysisMd, filename) {
    reportAnalysisResult.style.display = "block";
    const formattedHtml = marked.parse(analysisMd);
    const cleanSpeechText = analysisMd.replace(/[#*`_\[\]()>-]/g, " ").replace(/\s+/g, " ");

    reportAnalysisResult.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; border-bottom:1px solid #e2e8f0; padding-bottom:8px;">
        <div>
          <span style="font-weight:700; color:#0f172a; font-size:14px;">Diagnostic Findings for: ${escapeHtml(filename)}</span>
        </div>
        <div style="display:flex; gap:6px;">
          <button class="btn btn-outline" style="padding:4px 8px; font-size:11.5px;" onclick="window.speakReceptionistText(this)" data-text="${escapeHtml(cleanSpeechText)}">
            <i data-lucide="volume-2" style="width:13px;height:13px;"></i> Listen
          </button>
          <button class="btn btn-outline" style="padding:4px 8px; font-size:11.5px;" onclick="window.copyMessageText(this)" data-copy="${escapeHtml(analysisMd)}">
            <i data-lucide="copy" style="width:13px;height:13px;"></i> Copy
          </button>
        </div>
      </div>
      <div class="message-bubble" style="background:white; padding:14px; border-radius:8px;">
        ${formattedHtml}
      </div>
      <div style="margin-top:14px; display:flex; justify-content:space-between; align-items:center;">
        <button class="btn btn-primary" id="sendReportToChatBtn">
          <i data-lucide="message-square" style="width:14px;height:14px;"></i>
          Discuss Findings With Receptionist
        </button>
        <button class="btn btn-outline" onclick="document.getElementById('reportModal').classList.remove('active')">
          Close Window
        </button>
      </div>
    `;
    lucide.createIcons();

    document.getElementById("sendReportToChatBtn").addEventListener("click", () => {
      closeModal(reportModal);
      appendBotResponse({
        response: `### 📄 Medical Report Analysis: **${escapeHtml(filename)}**\n\n${analysisMd}\n\n💡 *Would you like me to book a consultation with one of our General Physicians or Specialists to review these results?*`,
        matched_doctors: []
      });
      scrollToBottom();
    });
  }

  // ----------------- My Reports History ----------------- //

  myReportsBtn.addEventListener("click", openMyReportsModal);

  async function openMyReportsModal() {
    if (!currentUser || !authToken) return;
    myReportsModal.classList.add("active");
    reportsHistoryList.innerHTML = `<div style="text-align:center; padding:20px; color:#64748b;">Loading your medical reports...</div>`;

    try {
      const res = await fetch(`/api/reports/history?user_email=${encodeURIComponent(currentUser.email)}`, {
        headers: { "Authorization": `Bearer ${authToken}` }
      });
      const data = await res.json();

      if (data.reports && data.reports.length > 0) {
        reportsHistoryList.innerHTML = "";
        data.reports.forEach((rep, idx) => {
          const item = document.createElement("div");
          item.style.cssText = "background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; display:flex; justify-content:space-between; align-items:center;";
          item.innerHTML = `
            <div>
              <div style="font-weight:700; color:#0f172a; font-size:13.5px;">${escapeHtml(rep.filename)}</div>
              <div style="font-size:11.5px; color:#64748b; margin-top:2px;">
                📅 Analyzed on: ${rep.created_at}
              </div>
            </div>
            <button class="btn btn-outline" style="font-size:12px; padding:4px 10px;" onclick="window.viewPastReport(${idx})">
              View Analysis
            </button>
          `;
          reportsHistoryList.appendChild(item);
        });

        window.cachedReports = data.reports;
      } else {
        reportsHistoryList.innerHTML = `
          <div style="text-align:center; padding:30px; color:#64748b;">
            <i data-lucide="file-x" style="width:32px;height:32px;margin:0 auto 8px;display:block;color:#94a3b8;"></i>
            No reports uploaded yet. Click <strong>"Analyze Report"</strong> above to upload your first lab report.
          </div>
        `;
        lucide.createIcons();
      }
    } catch (err) {
      reportsHistoryList.innerHTML = `<div style="text-align:center; padding:20px; color:#ef4444;">Failed to load report history.</div>`;
    }
  }

  window.viewPastReport = function(index) {
    if (!window.cachedReports || !window.cachedReports[index]) return;
    const rep = window.cachedReports[index];
    closeModal(myReportsModal);
    openReportModal();
    renderReportAnalysis(rep.analysis_result, rep.filename);
  };

  // ----------------- Doctors Directory ----------------- //

  async function loadDoctorsDirectory() {
    try {
      const res = await fetch("/api/doctors");
      allDoctorsCache = await res.json();
      renderDoctorsList(allDoctorsCache);
      populateDoctorSelect(allDoctorsCache);
    } catch (e) {
      console.error("Failed to load doctors", e);
    }
  }

  function renderDoctorsList(doctors) {
    modalDoctorsList.innerHTML = "";
    if (doctors.length === 0) {
      modalDoctorsList.innerHTML = `<div style="text-align:center; padding:20px; color:#64748b;">No doctors found matching criteria.</div>`;
      return;
    }

    doctors.forEach(doc => {
      const item = document.createElement("div");
      item.style.cssText = "background:#f8fafc; border:1px solid #e2e8f0; border-radius:10px; padding:12px; display:flex; justify-content:space-between; align-items:center;";
      item.innerHTML = `
        <div>
          <div style="font-weight:700; color:#0f172a; font-size:13.5px;">${escapeHtml(doc.name)}</div>
          <div style="font-size:12px; color:#0284c7; font-weight:600;">${escapeHtml(doc.specialization)} (${escapeHtml(doc.department_name)})</div>
          <div style="font-size:11.5px; color:#64748b; margin-top:2px;">
            ${escapeHtml(doc.qualification)} • ${doc.experience_years} yrs exp • Room: ${escapeHtml(doc.room_no)}
          </div>
          <div style="font-size:11.5px; color:#334155; margin-top:2px;">
            🕒 ${escapeHtml(doc.timings)} (${escapeHtml(doc.visiting_days)})
          </div>
        </div>
        <div style="text-align:right;">
          <div style="font-weight:700; color:#059669; font-size:13px; margin-bottom:6px;">₹${doc.consultation_fee}</div>
          <button class="btn btn-primary" style="padding:4px 10px; font-size:11.5px;" onclick="window.quickBookDoctor(${doc.id}, '${escapeHtml(doc.name)}')">
            Book
          </button>
        </div>
      `;
      modalDoctorsList.appendChild(item);
    });
  }

  docSearchInput.addEventListener("input", (e) => {
    const term = e.target.value.toLowerCase().trim();
    const filtered = allDoctorsCache.filter(d => 
      d.name.toLowerCase().includes(term) ||
      d.specialization.toLowerCase().includes(term) ||
      d.department_name.toLowerCase().includes(term)
    );
    renderDoctorsList(filtered);
  });

  // ----------------- Appointment Booking (Protected) ----------------- //

  function populateDoctorSelect(doctors) {
    apptDoctorSelect.innerHTML = `<option value="">-- Choose Doctor --</option>`;
    doctors.forEach(d => {
      const opt = document.createElement("option");
      opt.value = d.id;
      opt.textContent = `${d.name} (${d.specialization} - ₹${d.consultation_fee})`;
      apptDoctorSelect.appendChild(opt);
    });
  }

  window.quickBookDoctor = function(docId, docName) {
    closeModal(doctorsModal);
    appointmentModal.classList.add("active");
    apptDoctorSelect.value = docId;
  };

  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  const yyyy = tomorrow.getFullYear();
  const mm = String(tomorrow.getMonth() + 1).padStart(2, '0');
  const dd = String(tomorrow.getDate()).padStart(2, '0');
  document.getElementById("apptDate").value = `${yyyy}-${mm}-${dd}`;
  document.getElementById("apptDate").min = `${yyyy}-${mm}-${dd}`;

  appointmentForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const docId = apptDoctorSelect.value;
    const name = document.getElementById("apptPatientName").value.trim();
    const phone = document.getElementById("apptPatientPhone").value.trim();
    const date = document.getElementById("apptDate").value;
    const time = document.getElementById("apptTime").value;
    const reason = document.getElementById("apptReason").value.trim();

    try {
      const res = await fetch("/api/appointment", {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${authToken}`
        },
        body: JSON.stringify({
          patient_name: name,
          patient_phone: phone,
          doctor_id: parseInt(docId),
          appointment_date: date,
          appointment_time: time,
          reason: reason
        })
      });

      const data = await res.json();
      if (res.ok) {
        apptSuccessMessage.style.display = "block";
        apptSuccessMessage.innerHTML = `
          <strong>✅ Appointment Confirmed!</strong><br>
          Token #${data.appointment.id} for <strong>${escapeHtml(data.appointment.patient_name)}</strong> with 
          <strong>${escapeHtml(data.appointment.doctor_name)}</strong> on ${data.appointment.appointment_date} at ${data.appointment.appointment_time}.
        `;
        appointmentForm.reset();
        setTimeout(() => {
          apptSuccessMessage.style.display = "none";
          closeModal(appointmentModal);
          appendBotMessage(`### ✅ Appointment Confirmed (Token #${data.appointment.id})\n- **Patient:** ${data.appointment.patient_name}\n- **Doctor:** ${data.appointment.doctor_name} (${data.appointment.department})\n- **Schedule:** ${data.appointment.appointment_date} at ${data.appointment.appointment_time}`);
          scrollToBottom();
        }, 3000);
      } else {
        alert("Failed to book appointment: " + (data.detail || "Unknown error"));
      }
    } catch (err) {
      alert("Error booking appointment. Please try again.");
    }
  });

  // ----------------- Modal Open / Close Helpers ----------------- //

  emergencyBtn.addEventListener("click", () => emergencyModal.classList.add("active"));
  doctorsDirBtn.addEventListener("click", () => {
    doctorsModal.classList.add("active");
    if (allDoctorsCache.length === 0) loadDoctorsDirectory();
  });
  bookApptModalBtn.addEventListener("click", () => {
    appointmentModal.classList.add("active");
    if (allDoctorsCache.length === 0) loadDoctorsDirectory();
  });

  function closeModal(modal) {
    if (modal) modal.classList.remove("active");
  }

  document.querySelectorAll(".modal-close").forEach(btn => {
    btn.addEventListener("click", (e) => {
      const modalId = e.target.getAttribute("data-close");
      const target = document.getElementById(modalId);
      if (target) closeModal(target);
    });
  });

  document.querySelectorAll(".modal-overlay").forEach(overlay => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) closeModal(overlay);
    });
  });

  // ----------------- Quick Prompt Chips ----------------- //

  document.querySelectorAll(".chip-btn").forEach(btn => {
    if (btn.id === "chipUploadReport") return;
    btn.addEventListener("click", () => {
      const query = btn.getAttribute("data-query");
      if (query) handleSendMessage(query);
    });
  });

  // ----------------- Input & Voice Events ----------------- //

  sendBtn.addEventListener("click", () => handleSendMessage());

  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  if (voiceBtn && recognition) {
    voiceBtn.addEventListener("click", () => {
      if (isRecording) {
        recognition.stop();
      } else {
        recognition.start();
      }
    });
  }

  function escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
