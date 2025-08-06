const BACKEND_URL = "http://127.0.0.1:8000";
let mediaRecorder, audioChunks = [], dateProductie = { hours: [], values: [] }, chart;

const weekDays = {
  monday: "Monday",
  tuesday: "Tuesday",
  wednesday: "Wednesday",
  thursday: "Thursday",
  friday: "Friday",
  saturday: "Saturday",
  sunday: "Sunday"
};

async function startRecording() {
  document.getElementById("status").innerText = "🎧 Recording...";
  document.getElementById("result").innerText = "";
  clearPatternAndStats();
  document.getElementById("fallbackMessage").style.display = "none";
  document.getElementById("result").classList.add("hidden");
  document.getElementById("pattern").classList.add("hidden");
  document.getElementById("patternTitle").classList.add("hidden");
  document.getElementById("statistics").classList.add("hidden");
  document.getElementById("relevantStatistics").classList.add("hidden");
  document.getElementById("bonusThresholdInfo").classList.add("hidden");

  audioChunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
  mediaRecorder.onstop = async () => {
    document.getElementById("status").innerText = "⏳ Sending to server...";
    const blob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("file", blob, "audio.webm");
    try {
      const r = await fetch(`${BACKEND_URL}/transcribe`, { method: "POST", body: formData });
      const json = await r.json();
      const command = json.text;
      if (!command || command.trim() === "") {
        document.getElementById("fallbackMessage").style.display = "block";
        document.getElementById("status").innerText = "❗ Command not understood.";
        return;
      }
      document.getElementById("fallbackMessage").style.display = "none";
      executeCommand(command);
    } catch {
      document.getElementById("status").innerText = "❗ Transcription error.";
      document.getElementById("fallbackMessage").style.display = "none";
    }
  };
  mediaRecorder.start();
  setTimeout(() => mediaRecorder.stop(), 5000);
}

function sendCommand() {
  const command = document.getElementById("commandInput").value.trim();
  if (!command) {
    document.getElementById("status").innerText = "❗ Please enter a valid command.";
    document.getElementById("bonusThresholdInfo").classList.add("hidden");
    return;
  }
  executeCommand(command);
}

function clearPatternAndStats() {
  document.getElementById("pattern-device-1").innerHTML = "";
  document.getElementById("pattern-device-2").innerHTML = "";
  document.getElementById("statistics").innerHTML = "";
  document.getElementById("relevantStatistics").innerHTML = "";
}

async function executeCommand(command) {
  document.getElementById("status").innerText = "🔄 Processing command...";
  document.getElementById("bonusThresholdInfo").classList.add("hidden");
  document.getElementById("result").classList.add("hidden");
  document.getElementById("pattern").classList.add("hidden");
  document.getElementById("patternTitle").classList.add("hidden");
  document.getElementById("statistics").classList.add("hidden");
  document.getElementById("relevantStatistics").classList.add("hidden");
  document.getElementById("legend").classList.add("hidden");

  clearPatternAndStats();
  document.getElementById("fallbackMessage").style.display = "none";

  try {
    const r = await fetch(`${BACKEND_URL}/ai`, {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ command })
     });
    const json = await r.json();

    const thresholdEl = document.getElementById("bonusThresholdInfo");
    if ("bonus_threshold" in json && json.bonus_threshold !== null && !isNaN(json.bonus_threshold)) {
      thresholdEl.innerText = `📈 Minimum required energy threshold: ${json.bonus_threshold} kWh`;
      thresholdEl.classList.remove("hidden");
    } else {
      thresholdEl.innerText = "";
      thresholdEl.classList.add("hidden");
    }

    if (json.recommendations) {
      document.getElementById("legend").style.display = "block";
      document.getElementById("result").classList.remove("hidden");
      let html = `<h3>📋 Device recommendations</h3>`;
    const sorted = json.recommendations.sort((a, b) => new Date(`${a.date}T${a.time}`) - new Date(`${b.date}T${b.time}`));
      let grouped = {};
      sorted.forEach(r => {
        // group by the 'date' field
        const dayKey = r.date;
        if (!grouped[dayKey]) grouped[dayKey] = [];
        grouped[dayKey].push(r);
      });
      for (const dateKey of Object.keys(grouped)) {
        let dayArr = grouped[dateKey];
        dayArr.sort((a, b) => b.score - a.score);
        const displayDay = weekDays[(dayArr[0].day || "").toLowerCase()] || dayArr[0].day;
        html += `<h4>📅 ${dateKey} (${displayDay})</h4>`;
        dayArr.forEach(r => {
          let symbol = "🟡";
          if (r.holiday) {
            symbol = "🔴";
          } else if (r.habit) {
            symbol = "🟢";
          }
          html += `<p>${symbol} ${r.time} — estimated ${r.energy} kWh — score: ${r.score}</p>`;
        });
      }
      document.getElementById("result").innerHTML = html;
      document.getElementById("legend").classList.remove("hidden");
      document.getElementById("fallbackMessage").style.display = "none";
      const errorEl = document.getElementById("errorMessages");
      if (json.error_messages && json.error_messages.length > 0) {
        errorEl.innerText = json.error_messages.join("\n");
        document.getElementById("status").innerText = "⚠️ Command processed with warnings.";
      } else {
        errorEl.innerText = "";
        document.getElementById("status").innerText = "✅ Command processed.";
      }

    } else if (json.error) {
      document.getElementById("result").classList.add("hidden");
      document.getElementById("status").innerText = "⚠️ " + json.error;
      if (json.error.toLowerCase().includes("not understood")) {
        document.getElementById("fallbackMessage").style.display = "block";
      } else {
        document.getElementById("fallbackMessage").style.display = "none";
      }
    } else {
      document.getElementById("legend").style.display = "none";
      throw new Error("Unknown response from server");
    }

    if (json.patterns_per_day && json.statistics) {
      document.getElementById("patternTitle").classList.remove("hidden");
      showPatternsAndStats(json.patterns_per_day, json.statistics);
      document.getElementById("pattern").classList.remove("hidden");
      document.getElementById("statistics").classList.remove("hidden");
      document.getElementById("relevantStatistics").classList.remove("hidden");

    } else {
      document.getElementById("pattern").classList.add("hidden");
      document.getElementById("patternTitle").classList.add("hidden");
      document.getElementById("statistics").classList.add("hidden");
      document.getElementById("relevantStatistics").classList.add("hidden");
      document.getElementById("bonusThresholdInfo").innerText = "";
      document.getElementById("bonusThresholdInfo").classList.add("hidden");
    }

  } catch (e) {
    console.error("❌ Error in executeCommand:", e);
    document.getElementById("status").innerText = "❗ Error processing command.";
    document.getElementById("fallbackMessage").style.display = "none";
    document.getElementById("result").classList.add("hidden");
    document.getElementById("pattern").classList.add("hidden");
    document.getElementById("patternTitle").classList.add("hidden");
    document.getElementById("statistics").classList.add("hidden");
    document.getElementById("relevantStatistics").classList.add("hidden");
    document.getElementById("bonusThresholdInfo").innerText = "";
    document.getElementById("bonusThresholdInfo").classList.add("hidden");
    document.getElementById("legend").style.display = "none";
  }
}

function showPatternsAndStats(patternsPerDay, statistics) {
  const patternCont1 = document.getElementById("pattern-device-1");
  const patternCont2 = document.getElementById("pattern-device-2");
  const relevantStatsCont = document.getElementById("relevantStatistics");
  const permanentStatsCont = document.getElementById("statistics");

  const relevant = ["washing_machine", "dishwasher"];
  const permanent = ["fridge", "freezer", "boiler"];

  // Show patterns for relevant devices
  const devices = Object.keys(patternsPerDay).filter(d => relevant.includes(d));

  if (devices.length >= 1) {
    let html1 = `<h4>📌 ${devices[0]}</h4>`;
    let sortedDays1 = Object.values(patternsPerDay[devices[0]]).slice().sort((a, b) => b.total - a.total);
    sortedDays1.forEach(z => {
      const displayDay = weekDays[(z.day || "").toLowerCase()] || z.day;
      html1 += `<p><strong>📅 ${displayDay} — ${z.total} cycles</strong></p>`;
      z.hours.forEach(o => {
        html1 += `<p>🕓 hour ${o.hour} — ${o.cycle_count} cycles</p>`;
      });
    });
    patternCont1.innerHTML = html1;
  } else {
    patternCont1.innerHTML = "";
  }

  if (devices.length >= 2) {
    let html2 = `<h4>📌 ${devices[1]}</h4>`;
    let sortedDays2 = Object.values(patternsPerDay[devices[1]]).slice().sort((a, b) => b.total - a.total);
    sortedDays2.forEach(z => {
      const displayDay = weekDays[(z.day || "").toLowerCase()] || z.day;
      html2 += `<p><strong>📅 ${displayDay} — ${z.total} cycles</strong></p>`;
      z.hours.forEach(o => {
        html2 += `<p>🕓 hour ${o.hour} — ${o.cycle_count} cycles</p>`;
      });
    });
    patternCont2.innerHTML = html2;
  } else {
    patternCont2.innerHTML = "";
  }

  // Relevant stats below patterns
  let htmlRelevantStats = "";
  relevant.forEach(d => {
    if (statistics[d]) {
      const s = statistics[d];
      htmlRelevantStats += `<div class="stat-device">
        <h4>📈 ${d}</h4>
        <p>🕒 Average duration: ${s.avg_duration_min ?? "-"} minutes</p>
        <p>⚡ Average energy: ${s.avg_energy_kwh ?? "-"} kWh</p>
        <p>🔁 Number of cycles: ${s.cycle_count ?? "-"}</p>
      </div>`;
    }
  });
  relevantStatsCont.innerHTML = htmlRelevantStats;
  relevantStatsCont.classList.remove("hidden");

  // Permanent stats below chart
  let htmlPermanentStats = "";
  permanent.forEach(d => {
    if (statistics[d]) {
      const s = statistics[d];
      htmlPermanentStats += `<div class="stat-device">
        <h4>📈 ${d}</h4>
        <p>🕒 Average duration: ${s.avg_duration_min ?? "-"} minutes</p>
        <p>⚡ Average energy: ${s.avg_energy_kwh ?? "-"} kWh</p>
        <p>🔁 Number of cycles: ${s.cycle_count ?? "-"}</p>
      </div>`;
    }
  });
  permanentStatsCont.innerHTML = htmlPermanentStats;
  permanentStatsCont.classList.remove("hidden");
}

async function generateSolarProduction() {
  document.getElementById("status").innerText = "⏳ Generating production...";
  try {
    const r = await fetch(`${BACKEND_URL}/generate_solar_production`);
    const json = await r.json();
    console.log("Generation response:", json); // 🔍 debug
    if (json.status === "ok") {
      document.getElementById("status").innerText = "✅ Production generated.";
      await fetchProductionData();
      displayChart();
    } else {
      document.getElementById("status").innerText = "❌ Generation error.";
    }
  } catch (e) {
    console.error("Fetch error:", e);
    document.getElementById("status").innerText = "❌ Could not contact server.";
  }
}


async function fetchProductionData() {
  const r = await fetch(`${BACKEND_URL}/solar_production`);
  const json = await r.json();
  dateProductie = { hours: json.hours, values: json.values };
  const zile = [...new Set(json.hours.map(o => o.split(' ')[0]))];
  const select = document.getElementById("daySelect");
  select.style.display = "inline-block";
  select.innerHTML = '<option value="all">All days</option>';
  zile.forEach(z => {
    const opt = document.createElement("option");
    opt.value = z;
    opt.text = z;
    select.appendChild(opt);
  });
}

function displayChart() {
  const zi = document.getElementById("daySelect").value;
  const filtrate = dateProductie.hours.map((o, i) => ({ ora: o, val: dateProductie.values[i] })).filter(d => zi === "all" || d.ora.startsWith(zi));
  const labels = filtrate.map(d => d.ora);
  const valori = filtrate.map(d => d.val);
  const ctx = document.getElementById("productionChart").getContext("2d");
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels.map(o => o.split(" ")[0]),
      datasets: [{
        label: "Solar production (kWh)",
        data: valori,
        borderColor: "green",
        backgroundColor: "rgba(0,128,0,0.2)",
        tension: 0.3,
        fill: true,
        pointRadius: 2,
        pointHoverRadius: 5
      }]
    },
    options: {
      responsive: true,
      plugins: {
        tooltip: {
          callbacks: {
            title: ctx => filtrate[ctx[0].dataIndex].ora
          }
        }
      },
      scales: {
        x: { title: { display: true, text: "Day" } },
        y: { title: { display: true, text: "kWh" } }
      }
    }
  });
}
