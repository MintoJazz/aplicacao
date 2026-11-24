const e = performance.getEntriesByType("navigation")[0];
document.getElementById("proto").textContent = "nextHopProtocol: " + (e && e.nextHopProtocol);
