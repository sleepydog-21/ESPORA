/* ==========================================================================
   ESPORA Voice Note Recorder (MediaRecorder API -> Dash Hidden Input Bridge)
   ========================================================================== */
(function () {
    let mediaRecorder = null;
    let audioChunks = [];
    let activeStream = null;
    let timerInterval = null;
    let secondsElapsed = 0;

    function setNativeInputValue(el, value) {
        if (!el) return;
        const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
        setter.call(el, value);
        el.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function formatTime(sec) {
        const m = String(Math.floor(sec / 60)).padStart(2, "0");
        const s = String(sec % 60).padStart(2, "0");
        return `${m}:${s}`;
    }

    window.dash_clientside = window.dash_clientside || {};
    window.dash_clientside.voice = {
        startRecording: function (n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;

            const statusEl = document.getElementById("voice-status-text");
            const stopBtn = document.getElementById("btn-voice-stop");
            const startBtn = document.getElementById("btn-voice-start");
            const previewEl = document.getElementById("voice-preview-container");

            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                if (statusEl) statusEl.innerText = "⚠️ Tu navegador no soporta grabación de micrófono (usa subir archivo de audio).";
                return "unsupported";
            }

            navigator.mediaDevices.getUserMedia({ audio: true }).then(function (stream) {
                activeStream = stream;
                audioChunks = [];
                let mimeType = "";
                if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
                    mimeType = "audio/webm;codecs=opus";
                } else if (MediaRecorder.isTypeSupported("audio/webm")) {
                    mimeType = "audio/webm";
                } else if (MediaRecorder.isTypeSupported("audio/mp4")) {
                    mimeType = "audio/mp4";
                }

                mediaRecorder = mimeType ? new MediaRecorder(stream, { mimeType }) : new MediaRecorder(stream);

                mediaRecorder.ondataavailable = function (e) {
                    if (e.data && e.data.size > 0) {
                        audioChunks.push(e.data);
                    }
                };

                mediaRecorder.onstop = function () {
                    clearInterval(timerInterval);
                    const finalMime = (mediaRecorder.mimeType || "audio/webm").split(";")[0];
                    const ext = finalMime.includes("mp4") ? "m4a" : "webm";
                    const blob = new Blob(audioChunks, { type: finalMime });

                    const reader = new FileReader();
                    reader.onloadend = function () {
                        const dataUrl = reader.result;
                        const base64Data = dataUrl.split(",")[1];
                        const now = new Date();
                        const ts = now.toISOString().replace(/[:.]/g, "-").slice(0, 19);
                        const payload = JSON.stringify({
                            filename: `nota_voz_${ts}.${ext}`,
                            content_type: finalMime,
                            file_data: base64Data
                        });

                        const hiddenInput = document.getElementById("voice-recording-data");
                        setNativeInputValue(hiddenInput, payload);

                        if (previewEl) {
                            previewEl.innerHTML =
                                `<div class="p-2 bg-light rounded border mt-2">` +
                                `<div class="small fw-semibold text-success mb-1">✓ Nota de voz lista para guardar (${formatTime(secondsElapsed)}):</div>` +
                                `<audio controls style="width:100%;height:38px;" src="${dataUrl}"></audio>` +
                                `</div>`;
                        }
                        if (statusEl) statusEl.innerText = "✓ Grabación capturada. Haz clic en 'Guardar Nota en Expediente'.";
                    };
                    reader.readAsDataURL(blob);

                    if (activeStream) {
                        activeStream.getTracks().forEach(t => t.stop());
                        activeStream = null;
                    }
                    if (stopBtn) stopBtn.disabled = true;
                    if (startBtn) startBtn.disabled = false;
                };

                mediaRecorder.start();
                secondsElapsed = 0;
                if (previewEl) previewEl.innerHTML = "";
                if (stopBtn) stopBtn.disabled = false;
                if (startBtn) startBtn.disabled = true;
                if (statusEl) statusEl.innerText = "🔴 Grabando nota de voz... 00:00";

                clearInterval(timerInterval);
                timerInterval = setInterval(function () {
                    secondsElapsed += 1;
                    if (statusEl) statusEl.innerText = `🔴 Grabando nota de voz... ${formatTime(secondsElapsed)}`;
                }, 1000);
            }).catch(function (err) {
                if (statusEl) statusEl.innerText = "⚠️ Permiso de micrófono denegado o no disponible: " + err.message;
            });

            return "recording";
        },

        stopRecording: function (n_clicks) {
            if (!n_clicks) return window.dash_clientside.no_update;
            if (mediaRecorder && mediaRecorder.state !== "inactive") {
                mediaRecorder.stop();
            }
            return "stopped";
        }
    };
})();
