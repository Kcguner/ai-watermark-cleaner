(function () {
  "use strict";

  function lang() {
    var s = localStorage.getItem("lang");
    if (s && window.I18N && window.I18N[s]) return s;
    var n = (navigator.language || "en").slice(0, 2).toLowerCase();
    if (window.I18N && window.I18N[n]) return n;
    return "en";
  }

  function applyLang(l) {
    var dict = (window.I18N && (window.I18N[l] || window.I18N.en)) || {};
    document.documentElement.lang = l;
    document.querySelectorAll("[data-i18n]").forEach(function (el) {
      var k = el.getAttribute("data-i18n");
      if (dict[k]) el.textContent = dict[k];
    });
    var sel = document.getElementById("lang");
    if (sel) sel.value = l;
  }

  function t(key) {
    var l = lang();
    var d = window.I18N[l] || window.I18N.en;
    return d[key] || window.I18N.en[key] || key;
  }

  function filenameFromDisposition(h, fallback) {
    if (!h) return fallback;
    var m = /filename\*=UTF-8''([^;]+)|filename="?([^";]+)"?/.exec(h);
    if (!m) return fallback;
    try {
      return decodeURIComponent(m[1] || m[2]);
    } catch (e) {
      return m[1] || m[2] || fallback;
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var current = lang();
    applyLang(current);

    var langSel = document.getElementById("lang");
    if (langSel) {
      langSel.addEventListener("change", function () {
        current = langSel.value;
        localStorage.setItem("lang", current);
        applyLang(current);
      });
    }

    var form = document.getElementById("clean-form");
    var fileInput = document.getElementById("file");
    var drop = document.getElementById("drop");
    var status = document.getElementById("status");
    var preview = document.getElementById("preview");
    var btn = document.getElementById("submit-btn");

    if (drop && fileInput) {
      drop.addEventListener("click", function () { fileInput.click(); });
      ["dragover", "dragenter"].forEach(function (ev) {
        drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("drag"); });
      });
      ["dragleave", "drop"].forEach(function (ev) {
        drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("drag"); });
      });
      drop.addEventListener("drop", function (e) {
        if (e.dataTransfer && e.dataTransfer.files.length) {
          fileInput.files = e.dataTransfer.files;
          showPreview();
        }
      });
      fileInput.addEventListener("change", showPreview);
    }

    function showPreview() {
      if (!preview || !fileInput || !fileInput.files.length) return;
      var f = fileInput.files[0];
      if (f.type.indexOf("image/") === 0) {
        preview.src = URL.createObjectURL(f);
        preview.style.display = "block";
      } else {
        preview.style.display = "none";
        preview.removeAttribute("src");
      }
    }

    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        if (!fileInput.files.length) return;
        var fd = new FormData(form);
        status.textContent = t("working");
        btn.disabled = true;
        fetch("/api/clean", { method: "POST", body: fd })
          .then(function (r) {
            if (!r.ok) throw new Error("HTTP " + r.status);
            var disp = r.headers.get("content-disposition");
            var fallback = "cleaned";
            if (fileInput.files[0]) {
              var n = fileInput.files[0].name;
              var dot = n.lastIndexOf(".");
              fallback = (dot > 0 ? n.slice(0, dot) : n) + "_cleaned" + (dot > 0 ? n.slice(dot) : "");
            }
            var name = filenameFromDisposition(disp, fallback);
            return r.blob().then(function (b) { return { blob: b, name: name }; });
          })
          .then(function (res) {
            var url = URL.createObjectURL(res.blob);
            var a = document.createElement("a");
            a.href = url;
            a.download = res.name;
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(function () { URL.revokeObjectURL(url); }, 5000);
            status.textContent = t("done");
          })
          .catch(function () {
            status.textContent = t("error");
          })
          .finally(function () {
            btn.disabled = false;
          });
      });
    }
  });

  window.AWC = { applyLang: applyLang };
})();
