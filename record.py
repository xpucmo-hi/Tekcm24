import streamlit as st
import pydub
from streamlit_webrtc import WebRtcMode, webrtc_streamer

class WebRTCRecord:
    def __init__(self):
        self.webrtc_ctx = webrtc_streamer(
            key="sendonly-audio",
            mode=WebRtcMode.SENDONLY,
            audio_receiver_size=256,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.xten.com:3478"]}]},
            media_stream_constraints={
                "audio": True,
            },
        )

        if "audio_buffer" not in st.session_state:
            st.session_state["audio_buffer"] = pydub.AudioSegment.empty()

    def recording(self, filename):
        status_box = st.empty()

        while True:
            if self.webrtc_ctx.audio_receiver:
                try:
                    audio_frames = self.webrtc_ctx.audio_receiver.get_frames(timeout=1)
                except queue.Empty:
                    status_box.warning("No frame arrived.")
                    continue

                status_box.info("録音中...")

                sound_chunk = pydub.AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = pydub.AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=len(audio_frame.layout.channels),
                    )
                    sound_chunk += sound

                if len(sound_chunk) > 0:
                    st.session_state["audio_buffer"] += sound_chunk
            else:
                break

        audio_buffer = st.session_state["audio_buffer"]

        if not self.webrtc_ctx.state.playing and len(audio_buffer) > 0:
            status_box.empty()
            try:
                audio_buffer.export(filename, format="wav")
            except BaseException:
                st.error("Error while Writing wav to disk")

            # Reset
            st.session_state["audio_buffer"] = pydub.AudioSegment.empty()
