// Main JavaScript functionality for the Attendance Tracker

document.addEventListener("DOMContentLoaded", () => {
  // Initialize the application
  initializeApp()
})

function initializeApp() {
  // Auto-hide alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert")
  alerts.forEach((alert) => {
    setTimeout(() => {
      alert.style.opacity = "0"
      setTimeout(() => {
        alert.remove()
      }, 300)
    }, 5000)
  })

  // Initialize tooltips
  initializeTooltips()

  // Load smart suggestions periodically
  if (document.querySelector(".dashboard")) {
    loadSmartSuggestions()
    setInterval(loadSmartSuggestions, 30000) // Refresh every 30 seconds
  }
}

function initializeTooltips() {
  const tooltipElements = document.querySelectorAll("[title]")
  tooltipElements.forEach((element) => {
    element.addEventListener("mouseenter", showTooltip)
    element.addEventListener("mouseleave", hideTooltip)
  })
}

function showTooltip(event) {
  const tooltip = document.createElement("div")
  tooltip.className = "tooltip"
  tooltip.textContent = event.target.getAttribute("title")
  tooltip.style.position = "absolute"
  tooltip.style.background = "#333"
  tooltip.style.color = "white"
  tooltip.style.padding = "5px 10px"
  tooltip.style.borderRadius = "4px"
  tooltip.style.fontSize = "12px"
  tooltip.style.zIndex = "1000"
  tooltip.style.pointerEvents = "none"

  document.body.appendChild(tooltip)

  const rect = event.target.getBoundingClientRect()
  tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + "px"
  tooltip.style.top = rect.top - tooltip.offsetHeight - 5 + "px"

  event.target.removeAttribute("title")
  event.target.setAttribute("data-original-title", tooltip.textContent)
}

function hideTooltip(event) {
  const tooltip = document.querySelector(".tooltip")
  if (tooltip) {
    tooltip.remove()
  }

  const originalTitle = event.target.getAttribute("data-original-title")
  if (originalTitle) {
    event.target.setAttribute("title", originalTitle)
    event.target.removeAttribute("data-original-title")
  }
}

async function loadSmartSuggestions() {
  try {
    const response = await fetch("/api/suggestions/")
    const data = await response.json()

    if (data.suggestions && data.suggestions.length > 0) {
      updateSuggestionsDisplay(data.suggestions)
    }
  } catch (error) {
    console.error("Error loading suggestions:", error)
  }
}

function updateSuggestionsDisplay(suggestions) {
  const suggestionsContainer = document.querySelector(".suggestions-grid")
  if (!suggestionsContainer) return

  // Clear existing suggestions
  suggestionsContainer.innerHTML = ""

  suggestions.forEach((suggestion) => {
    const suggestionCard = createSuggestionCard(suggestion)
    suggestionsContainer.appendChild(suggestionCard)
  })
}

function createSuggestionCard(suggestion) {
  const card = document.createElement("div")
  card.className = `suggestion-card ${suggestion.type === "critical" ? "high" : "low"}`

  const icon =
    suggestion.type === "critical"
      ? "fas fa-exclamation-triangle"
      : suggestion.type === "warning"
        ? "fas fa-exclamation-circle"
        : "fas fa-check-circle"

  card.innerHTML = `
        <div class="suggestion-header">
            <h4>${suggestion.course_name}</h4>
            <i class="${icon}"></i>
        </div>
        <p>${suggestion.message}</p>
    `

  return card
}

// Form validation
function validateCourseForm(form) {
  const name = form.querySelector('input[name="name"]').value.trim()
  const totalLectures = Number.parseInt(form.querySelector('input[name="total_lectures"]').value)
  const attendedLectures = Number.parseInt(form.querySelector('input[name="attended_lectures"]').value)

  if (!name) {
    showAlert("Course name is required", "error")
    return false
  }

  if (totalLectures < 0) {
    showAlert("Total lectures cannot be negative", "error")
    return false
  }

  if (attendedLectures < 0) {
    showAlert("Attended lectures cannot be negative", "error")
    return false
  }

  if (attendedLectures > totalLectures) {
    showAlert("Attended lectures cannot exceed total lectures", "error")
    return false
  }

  return true
}

function showAlert(message, type = "info") {
  const alertContainer = document.querySelector(".messages") || createAlertContainer()

  const alert = document.createElement("div")
  alert.className = `alert alert-${type}`
  alert.innerHTML = `
        <i class="fas fa-info-circle"></i>
        ${message}
        <button class="alert-close" onclick="this.parentElement.remove()">×</button>
    `

  alertContainer.appendChild(alert)

  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (alert.parentElement) {
      alert.style.opacity = "0"
      setTimeout(() => alert.remove(), 300)
    }
  }, 5000)
}

function createAlertContainer() {
  const container = document.createElement("div")
  container.className = "messages"
  document.querySelector(".main-content").insertBefore(container, document.querySelector(".main-content").firstChild)
  return container
}

// Keyboard shortcuts
document.addEventListener("keydown", (event) => {
  // Ctrl/Cmd + N to add new course
  if ((event.ctrlKey || event.metaKey) && event.key === "n") {
    event.preventDefault()
    const addCourseButton = document.querySelector('[onclick="openAddCourseModal()"]')
    if (addCourseButton) {
      addCourseButton.click()
    }
  }

  // Escape to close modals
  if (event.key === "Escape") {
    const openModals = document.querySelectorAll('.modal[style*="flex"]')
    openModals.forEach((modal) => {
      modal.style.display = "none"
    })
  }
})

// Progress bar animation
function animateProgressBars() {
  const progressBars = document.querySelectorAll(".progress-fill")
  progressBars.forEach((bar) => {
    const width = bar.style.width
    bar.style.width = "0%"
    setTimeout(() => {
      bar.style.width = width
    }, 100)
  })
}

// Call animation when page loads
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(animateProgressBars, 500)
})

// Local storage for user preferences
function saveUserPreference(key, value) {
  localStorage.setItem(`attendance_tracker_${key}`, JSON.stringify(value))
}

function getUserPreference(key, defaultValue = null) {
  const stored = localStorage.getItem(`attendance_tracker_${key}`)
  return stored ? JSON.parse(stored) : defaultValue
}

// Theme toggle (if implemented)
function toggleTheme() {
  const currentTheme = getUserPreference("theme", "light")
  const newTheme = currentTheme === "light" ? "dark" : "light"

  document.body.setAttribute("data-theme", newTheme)
  saveUserPreference("theme", newTheme)
}

// Initialize theme on page load
document.addEventListener("DOMContentLoaded", () => {
  const savedTheme = getUserPreference("theme", "light")
  document.body.setAttribute("data-theme", savedTheme)
})

// Export data functionality
function exportAttendanceData() {
  const courses = Array.from(document.querySelectorAll(".course-card")).map((card) => {
    const name = card.querySelector("h3").textContent
    const percentage = card.querySelector(".percentage").textContent
    const stats = card.querySelectorAll(".lecture-stats span")
    const attended = stats[0] ? stats[0].textContent.replace(/\D/g, "") : "0"
    const total = stats[1] ? stats[1].textContent.replace(/\D/g, "") : "0"

    return {
      name,
      percentage,
      attended: Number.parseInt(attended),
      total: Number.parseInt(total),
    }
  })

  const dataStr = JSON.stringify(courses, null, 2)
  const dataBlob = new Blob([dataStr], { type: "application/json" })

  const link = document.createElement("a")
  link.href = URL.createObjectURL(dataBlob)
  link.download = `attendance_data_${new Date().toISOString().split("T")[0]}.json`
  link.click()
}

// Print functionality
function printAttendanceReport() {
  const printWindow = window.open("", "_blank")
  const courses = document.querySelectorAll(".course-card")

  let reportHTML = `
        <html>
        <head>
            <title>Attendance Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { text-align: center; margin-bottom: 30px; }
                .course { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; }
                .course-name { font-size: 18px; font-weight: bold; margin-bottom: 10px; }
                .stats { display: flex; justify-content: space-between; }
                .percentage { font-size: 24px; font-weight: bold; }
                .safe { color: green; }
                .danger { color: red; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Attendance Report</h1>
                <p>Generated on ${new Date().toLocaleDateString()}</p>
            </div>
    `

  courses.forEach((course) => {
    const name = course.querySelector("h3").textContent
    const percentage = course.querySelector(".percentage").textContent
    const isDanger = course.classList.contains("danger")
    const stats = course.querySelectorAll(".lecture-stats span")
    const attended = stats[0] ? stats[0].textContent : "0"
    const total = stats[1] ? stats[1].textContent : "0"

    reportHTML += `
            <div class="course">
                <div class="course-name">${name}</div>
                <div class="stats">
                    <span class="percentage ${isDanger ? "danger" : "safe"}">${percentage}</span>
                    <span>Attended: ${attended}</span>
                    <span>Total: ${total}</span>
                </div>
            </div>
        `
  })

  reportHTML += "</body></html>"

  printWindow.document.write(reportHTML)
  printWindow.document.close()
  printWindow.print()
}

// Service Worker registration for offline functionality (optional)
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/static/js/sw.js")
      .then((registration) => {
        console.log("ServiceWorker registration successful")
      })
      .catch((error) => {
        console.log("ServiceWorker registration failed")
      })
  })
}
