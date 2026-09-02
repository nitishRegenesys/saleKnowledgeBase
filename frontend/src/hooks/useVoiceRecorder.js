import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";


const TARGET_SAMPLE_RATE = 16000;


function downsampleTo16k(
  source,
  sourceRate
) {
  if (sourceRate === TARGET_SAMPLE_RATE) {
    return source;
  }

  const ratio =
    sourceRate / TARGET_SAMPLE_RATE;

  const outputLength = Math.floor(
    source.length / ratio
  );

  const output =
    new Float32Array(outputLength);

  for (let i = 0; i < outputLength; i++) {
    const start = Math.floor(i * ratio);
    const end = Math.floor(
      (i + 1) * ratio
    );

    let sum = 0;
    let count = 0;

    for (
      let j = start;
      j < end && j < source.length;
      j++
    ) {
      sum += source[j];
      count += 1;
    }

    output[i] =
      count > 0 ? sum / count : 0;
  }

  return output;
}


function floatToPcm16(chunks) {
  const total = chunks.reduce(
    (sum, chunk) =>
      sum + chunk.length,
    0
  );

  const bytes =
    new Uint8Array(total * 2);

  let offset = 0;

  for (const samples of chunks) {
    for (let i = 0; i < samples.length; i++) {
      let value = Math.max(
        -1,
        Math.min(
          1,
          samples[i]
        )
      );

      value =
        value < 0
          ? value * 0x8000
          : value * 0x7fff;

      const int16 =
        Math.round(value) & 0xffff;

      bytes[offset++] =
        int16 & 0xff;

      bytes[offset++] =
        (int16 >> 8) & 0xff;
    }
  }

  return bytes;
}


function bytesToBase64(bytes) {
  let binary = "";

  const chunkSize = 0x8000;

  for (
    let i = 0;
    i < bytes.length;
    i += chunkSize
  ) {
    binary += String.fromCharCode(
      ...bytes.subarray(i, i + chunkSize)
    );
  }

  return btoa(binary);
}


function useVoiceRecorder({
  onFrame,
  onError,
}) {
  const [isRecording, setIsRecording] =
    useState(false);

  const [isRequesting, setIsRequesting] =
    useState(false);

  const [error, setError] =
    useState(null);

  const streamRef = useRef(null);
  const contextRef = useRef(null);
  const processorRef = useRef(null);

  const onFrameRef = useRef(onFrame);
  const onErrorRef = useRef(onError);

  useEffect(() => {
    onFrameRef.current = onFrame;
    onErrorRef.current = onError;
  }, [onFrame, onError]);


  // ==========================================================
  // Cleanup recording resources. No auto-stop timer: the mic
  // keeps streaming until the user explicitly stops it.
  // ==========================================================

  const cleanup = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current
        .getTracks()
        .forEach((track) => track.stop());

      streamRef.current = null;
    }

    if (contextRef.current) {
      try {
        contextRef.current.close();
      } catch {
        // Ignore close errors
      }

      contextRef.current = null;
    }

    setIsRecording(false);
    setIsRequesting(false);
  }, []);


  useEffect(() => {
    return () => {
      cleanup();
      onFrameRef.current = null;
      onErrorRef.current = null;
    };
  }, [cleanup]);


  // ==========================================================
  // Stop recording (keeps any captured frames flowing via
  // onStop callback passed at call time)
  // ==========================================================

  const stopRecording = useCallback(() => {
    cleanup();
  }, [cleanup]);


  // ==========================================================
  // Start recording from the microphone. Each PCM16 16kHz
  // frame is encoded to base64 and handed to `onFrame` so the
  // caller can stream it over the voice WebSocket immediately.
  // ==========================================================

  const startRecording = useCallback(
    async () => {
      setError(null);

      try {
        if (
          !navigator.mediaDevices ||
          !navigator.mediaDevices.getUserMedia
        ) {
          throw new Error(
            "Microphone capture is not supported in this browser."
          );
        }

        const AudioContextClass =
          window.AudioContext ||
          window.webkitAudioContext;

        if (!AudioContextClass) {
          throw new Error(
            "Web Audio is not supported in this browser."
          );
        }

        setIsRequesting(true);

        const stream =
          await navigator.mediaDevices.getUserMedia({
            audio: {
              channelCount: 1,
              echoCancellation: true,
              noiseSuppression: true,
              sampleRate: TARGET_SAMPLE_RATE,
            },
          });

        // Surface unexpected track loss (device unplugged,
        // permission revoked) instead of failing silently.
        // NOTE: track.stop() does NOT fire `ended`, so this
        // only triggers for genuine external causes.
        stream.getAudioTracks().forEach((track) => {
          track.onended = () => {
            if (streamRef.current !== stream) {
              return;
            }

            cleanup();

            const trackError =
              "Microphone access ended unexpectedly.";

            setError(trackError);

            if (onErrorRef.current) {
              onErrorRef.current(trackError);
            }
          };
        });

        const context =
          new AudioContextClass();

        const source =
          context.createMediaStreamSource(
            stream
          );

        const processor =
          context.createScriptProcessor(
            4096,
            1,
            1
          );

        const sourceRate =
          context.sampleRate;

        processor.onaudioprocess = (
          event
        ) => {
          const input =
            event.inputBuffer.getChannelData(
              0
            );

          const resampled =
            downsampleTo16k(
              input,
              sourceRate
            );

          const pcmBytes =
            floatToPcm16([resampled]);

          const frameBase64 =
            bytesToBase64(pcmBytes);

          if (onFrameRef.current) {
            try {
              onFrameRef.current(
                frameBase64
              );
            } catch (err) {
              console.error(
                "Audio frame handler error:",
                err
              );
            }
          }
        };

        processor.connect(
          context.destination
        );

        source.connect(processor);

        streamRef.current = stream;
        contextRef.current = context;
        processorRef.current = processor;

        setIsRecording(true);
        setIsRequesting(false);
      } catch (err) {
        console.error(
          "Mic start error:",
          err
        );

        setIsRequesting(false);
        setIsRecording(false);

        const message =
          err?.message ||
          "Unable to access the microphone.";

        setError(message);

        if (onErrorRef.current) {
          onErrorRef.current(message);
        }

        if (streamRef.current) {
          streamRef.current
            .getTracks()
            .forEach((track) => track.stop());

          streamRef.current = null;
        }
      }
    },
    [cleanup]
  );


  return {
    isRecording,
    isRequesting,
    error,
    startRecording,
    stopRecording,
  };
}


export default useVoiceRecorder;