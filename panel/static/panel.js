// panel.js: the buttons on the page call the Python /api/... routes in panel.py.

// Every API call sends the X-Robot-Panel header (see require_panel_header in panel.py).
async function api(method, path, body) {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json", "X-Robot-Panel": "1" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await response.json().catch(() => ({ ok: false, error: `HTTP ${response.status}` }));
  if (!data.ok) throw new Error(data.error || "request failed");
  return data;
}

const $ = (id) => document.getElementById(id);

// Show "Working..." on a button while something runs.
async function busy(button, label, work) {
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  try { return await work(); } finally { button.disabled = false; button.textContent = original; }
}

// ---------------------------------------------------------------- connection

function showConnection(c) {
  const pill = $("conn-pill");
  if (c.connected) {
    pill.className = "pill pill-ok";
    pill.textContent = `● ${c.user}@${c.host}`;
    $("conn-detail").textContent = `Connected with ${c.auth_method}.` +
      (c.has_password ? " A password is held in memory." : "");
  } else {
    pill.className = "pill pill-fail";
    pill.textContent = "● Not connected";
    $("conn-detail").textContent = c.error || "Not connected yet.";
  }
  $("host").value = c.host;
  $("user").value = c.user;
}

$("conn-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const button = event.submitter;
  await busy(button, "Connecting…", async () => {
    try {
      const c = await api("POST", "/api/connection", {
        host: $("host").value, user: $("user").value, password: $("password").value,
      });
      showConnection(c);
    } catch (e) {
      showConnection({ connected: false, host: $("host").value, user: $("user").value, error: e.message });
    }
    $("password").value = "";  // don't leave it sitting in the page
  });
});

$("forget").addEventListener("click", async () => {
  showConnection(await api("POST", "/api/password/forget"));
  $("conn-detail").textContent += " Password forgotten.";
});

// Check the connection when the page opens (the panel tries to connect at start-up).
async function refreshConnection() {
  try { showConnection(await api("GET", "/api/connection")); } catch (e) { /* panel not ready */ }
}
refreshConnection();
setTimeout(refreshConnection, 2500);

// ---------------------------------------------------------------- status

function renderChecks(list) {
  const ul = $("checks");
  ul.innerHTML = "";
  for (const c of list) {
    const li = document.createElement("li");
    li.className = "check-item";
    const dot = document.createElement("span");
    dot.className = `dot ${c.state}`;
    dot.title = c.state;
    const name = document.createElement("span");
    name.className = "check-name";
    name.textContent = c.name;
    const detail = document.createElement("span");
    detail.className = "check-detail";
    detail.textContent = c.detail;  // textContent, never innerHTML: output can't inject HTML
    li.append(dot, name, detail);
    ul.append(li);
  }
}

$("run-checks").addEventListener("click", (event) =>
  busy(event.target, "Checking…", async () => {
    try {
      const data = await api("POST", "/api/status");
      renderChecks(data.checks);
      showConnection(data.connection);
      $("checks-time").textContent = `Checked in ${data.took_s} s at ${new Date().toLocaleTimeString()}.`;
    } catch (e) {
      renderChecks([{ name: "Status", state: "fail", detail: e.message }]);
    }
  })
);

// ---------------------------------------------------------------- tests

async function followJob(jobId) {
  const log = $("test-log");
  let since = 0;
  while (true) {
    const job = await api("GET", `/api/jobs/${jobId}?since=${since}`);
    if (job.lines.length) {
      log.textContent += job.lines.join("\n") + "\n";
      log.scrollTop = log.scrollHeight;
    }
    since = job.next;
    if (job.done) return job;
    await new Promise((resolve) => setTimeout(resolve, 400));
  }
}

for (const button of document.querySelectorAll("[data-tests]")) {
  button.addEventListener("click", () =>
    busy(button, "Running…", async () => {
      const result = $("test-result");
      $("test-log").textContent = "";
      result.className = "result";
      result.textContent = "Running…";
      try {
        const { job_id } = await api("POST", `/api/tests/${button.dataset.tests}`);
        const job = await followJob(job_id);
        const passed = job.exit_code === 0;
        result.className = `result ${passed ? "ok" : "fail"}`;
        result.textContent = `${job.title}: ${passed ? "all passed ✓" : `FAILED (exit code ${job.exit_code})`}`;
      } catch (e) {
        result.className = "result fail";
        result.textContent = e.message;
      }
    })
  );
}

// ---------------------------------------------------------------- camera

// Remember the rotation for each camera in this browser (just a convenience;
// if the browser blocks storage, it simply resets to "No rotation").
function savedRotation(camera) {
  try { return localStorage.getItem(`rotate-${camera}`) || "0"; } catch (e) { return "0"; }
}
$("rotate").value = savedRotation($("camera").value);
$("camera").addEventListener("change", () => { $("rotate").value = savedRotation($("camera").value); });
$("rotate").addEventListener("change", () => {
  try { localStorage.setItem(`rotate-${$("camera").value}`, $("rotate").value); } catch (e) { /* ignore */ }
});

$("snap").addEventListener("click", (event) =>
  busy(event.target, "Capturing…", async () => {
    const info = $("snap-info");
    info.textContent = "Taking a photo on the Pi…";
    try {
      const data = await api("POST", "/api/snapshot", {
        camera: $("camera").value, detect: $("detect").checked, rotate: Number($("rotate").value),
      });
      const img = $("snap-img");
      img.src = data.image;
      img.alt = `${$("camera").selectedOptions[0].text} snapshot`;
      img.hidden = false;
      let text = `${data.width}×${data.height}, captured in ${data.capture_s} s.`;
      if (data.people !== null) {
        text += ` People found: ${data.people} (${data.method}).`;
      }
      info.textContent = text;
    } catch (e) {
      info.textContent = `Snapshot failed: ${e.message}`;
    }
  })
);
