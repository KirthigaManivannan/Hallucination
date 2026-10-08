// Frontend logic. Model output is only ever inserted with textContent,
// never innerHTML, so it cannot inject HTML or scripts into the page.
(function () {
  "use strict";

  var form = document.getElementById("compare-form");
  var textarea = document.getElementById("question");
  var button = document.getElementById("compare-btn");
  var counter = document.getElementById("counter");
  var errorBox = document.getElementById("error");
  var loading = document.getElementById("loading");
  var results = document.getElementById("results");
  var disclaimer = document.getElementById("disclaimer");
  var guessingBox = document.getElementById("guessing-answer");
  var cautiousBox = document.getElementById("cautious-answer");
  var maxLength = parseInt(textarea.getAttribute("maxlength"), 10) || 500;

  function updateCounter() {
    var len = textarea.value.length;
    counter.textContent = len + " / " + maxLength;
    counter.classList.toggle("near-limit", len > maxLength * 0.9);
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  function clearError() {
    errorBox.textContent = "";
    errorBox.hidden = true;
  }

  function setLoading(isLoading) {
    loading.hidden = !isLoading;
    button.disabled = isLoading;
    button.textContent = isLoading ? "Comparing\u2026" : "Compare answers";
  }

  function fillAnswer(box, result) {
    box.classList.remove("failed");
    if (result && result.ok && typeof result.answer === "string") {
      box.textContent = result.answer;
    } else {
      box.classList.add("failed");
      var msg = result && typeof result.error === "string" ? result.error : "No answer received.";
      box.textContent = "This agent could not answer: " + msg;
    }
  }

  textarea.addEventListener("input", updateCounter);

  // Ctrl+Enter / Cmd+Enter submits.
  textarea.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (chip) {
    chip.addEventListener("click", function () {
      textarea.value = chip.getAttribute("data-q") || "";
      updateCounter();
      textarea.focus();
    });
  });

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    clearError();

    var question = textarea.value.trim();
    if (!question) {
      showError("Please enter a question.");
      textarea.focus();
      return;
    }
    if (question.length > maxLength) {
      showError("Question is too long. Please keep it under " + maxLength + " characters.");
      return;
    }

    results.hidden = true;
    disclaimer.hidden = true;
    setLoading(true);

    fetch("/api/compare", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: question })
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () { return {}; })
          .then(function (data) { return { ok: response.ok, data: data }; });
      })
      .then(function (res) {
        if (!res.ok) {
          showError(res.data && res.data.error ? res.data.error : "Something went wrong. Please try again.");
          return;
        }
        fillAnswer(guessingBox, res.data.guessing);
        fillAnswer(cautiousBox, res.data.cautious);
        results.hidden = false;
        disclaimer.hidden = false;
        results.scrollIntoView({ behavior: "smooth", block: "start" });
      })
      .catch(function () {
        showError("Could not reach the server. Check your connection and try again.");
      })
      .then(function () {
        setLoading(false);
      });
  });

  updateCounter();
})();
