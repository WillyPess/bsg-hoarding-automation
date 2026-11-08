// The job form: the bottom bar asks the engine (POST /jobs/estimate) for its numbers as the form is filled in, and the
// chosen photo is shown before it is sent. Nothing is computed here: the page only shows what the server answers.
(function () {
  var form = document.querySelector("form.job");
  if (!form) return;
  var timer = null, asked = 0;
  function show(values) {
    form.querySelectorAll("[data-est]").forEach(function (el) {
      var v = values && values[el.getAttribute("data-est")];
      el.textContent = v === undefined || v === null || v === "" ? "–" : v;
    });
  }
  function ask() {
    var mine = ++asked, data = new FormData(form);
    data.delete("photo");
    fetch("/jobs/estimate", { method: "POST", body: data, credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (mine === asked) show(j); })
      .catch(function () {});
  }
  function later() { clearTimeout(timer); timer = setTimeout(ask, 300); }
  form.addEventListener("input", later);
  form.addEventListener("change", later);
  ask();
  var site = form.querySelector("select[name=site]"), other = form.querySelector("input[name=site_other]");
  if (site && other) site.addEventListener("change", function () { other.hidden = site.value !== "other"; });
  var file = form.querySelector(".drop input[type=file]"), drop = form.querySelector(".drop");
  if (file && drop) file.addEventListener("change", function () {
    if (file.files && file.files[0]) { drop.querySelector("img").src = URL.createObjectURL(file.files[0]); drop.classList.add("has"); }
  });
})();
