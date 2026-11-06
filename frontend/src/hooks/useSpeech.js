import { useCallback, useRef, useState } from 'react'

export function useSpeech(onResult) {
  const [listening, setListening] = useState(false)
  const [supported] = useState(() => Boolean(window.SpeechRecognition || window.webkitSpeechRecognition))
  const recognitionRef = useRef(null)

  const startListening = useCallback(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!Recognition) return false
    const recognition = new Recognition()
    recognition.lang = 'te-IN'
    recognition.interimResults = false
    recognition.maxAlternatives = 1
    recognition.onresult = (event) => onResult(event.results[0][0].transcript)
    recognition.onend = () => setListening(false)
    recognition.onerror = () => setListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setListening(true)
    return true
  }, [onResult])

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop()
    setListening(false)
  }, [])

  const speak = useCallback((text) => {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'te-IN'
    utterance.rate = 0.9
    window.speechSynthesis.speak(utterance)
  }, [])

  return { listening, supported, startListening, stopListening, speak }
}
