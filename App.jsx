import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, CheckCircle, RefreshCw, Volume2, ArrowRight, ArrowLeft, AudioLines, BookOpen, Repeat, MessagesSquare, Image as ImageIcon, User, Globe2, Lock } from 'lucide-react';

const REGIONS_ACCENTS = [
  { id: 'dakar', name: 'Dakar', accent: 'Urbain' },
  { id: 'kaolack', name: 'Kaolack', accent: 'Saloum' },
  { id: 'saintlouis', name: 'Saint-Louis', accent: 'Ndar' },
  { id: 'baol', name: 'Diourbel / Baol', accent: 'Baol-Baol' },
  { id: 'cayor', name: 'Thiès / Cayor', accent: 'Cajor' },
  { id: 'casamance', name: 'Casamance', accent: 'Fogny' },
  { id: 'tamba', name: 'Tambacounda', accent: 'Oriental' }
];

const PROMPTS_PAR_MODE = {
  reading: [
    { id: 'r1', text: 'Naka nga def?', type: 'text' },
    { id: 'r2', text: 'Mangi fi rek, jërëjëf.', type: 'text' }
  ],
  repetition: [
    { id: 'rep1', text: 'Am nga jamm?', type: 'audio_guide' },
    { id: 'rep2', text: 'Lu bees ci dëkk bi?', type: 'audio_guide' }
  ],
  spontaneous: [
    { id: 's1', text: 'Parlez librement de votre journée en Wolof (30 secondes maximum).', type: 'free' },
    { id: 's2', text: 'Racontez une tradition marquante de votre région d\'origine.', type: 'free' }
  ],
  image_description: [
    { id: 'img1', text: 'Décrivez ce que vous voyez sur cette image en Wolof.', imageUrl: 'https://images.unsplash.com/photo-1542601906990-b4d3fb778b09?w=500&q=80', type: 'image' },
    { id: 'img2', text: 'Décrivez l\'activité de cette scène de marché traditionnelle.', imageUrl: 'https://images.unsplash.com/photo-1533777857889-4be7c70b33f7?w=500&q=80', type: 'image' }
  ]
};

export default function App() {
  const [step, setStep] = useState('gatekeeper');
  const [accessCode, setAccessCode] = useState('');

  const [birthYear, setBirthYear] = useState('2000');
  const [gender, setGender] = useState('M');
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [literacy, setLiteracy] = useState('reader');

  const [speechType, setSpeechType] = useState('reading');
  const [currentPromptIdx, setCurrentPromptIdx] = useState(0);
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [isPlayingPrompt, setIsPlayingPrompt] = useState(false);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  const promptsDisponibles = PROMPTS_PAR_MODE[speechType] || [];
  const currentPrompt = promptsDisponibles[currentPromptIdx] || { text: '' };

  useEffect(() => {
    if (literacy === 'non_reader' && speechType === 'reading') {
      setSpeechType('repetition');
    }
  }, [literacy]);

  useEffect(() => {
    stopPromptAudio();
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingDuration(0);
  }, [currentPromptIdx, speechType]);

  const togglePromptAudio = () => {
    if (isPlayingPrompt) {
      stopPromptAudio();
    } else {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(currentPrompt.text);
      utterance.lang = 'fr-FR';
      utterance.rate = 0.85;
      utterance.onstart = () => setIsPlayingPrompt(true);
      utterance.onend = () => setIsPlayingPrompt(false);
      window.speechSynthesis.speak(utterance);
    }
  };

  const stopPromptAudio = () => {
    window.speechSynthesis.cancel();
    setIsPlayingPrompt(false);
  };

  const startRecording = async () => {
    stopPromptAudio();
    audioChunksRef.current = [];
    setRecordingDuration(0);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      mediaRecorderRef.current.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };
      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        setAudioUrl(URL.createObjectURL(blob));
        clearInterval(timerRef.current);
      };
      mediaRecorderRef.current.start();
      setIsRecording(true);
      timerRef.current = setInterval(() => { setRecordingDuration((p) => p + 1); }, 1000);
    } catch (err) {
      alert("Erreur d'accès au micro.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
      clearInterval(timerRef.current);
    }
  };

  const handleCheckCode = () => {
    if (accessCode.trim() === 'WOLOF2026') {
      setStep('welcome');
    } else {
      alert("Code d'accès incorrect.");
    }
  };

  const validateAndNext = async () => {
    if (!audioBlob || !selectedRegion) return;
    if (recordingDuration < 1) {
      alert("⚠️ Audio trop court.");
      return;
    }

    const calculatedAge = new Date().getFullYear() - parseInt(birthYear);
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('transcript', speechType === 'spontaneous' || speechType === 'image_description' ? '[Spontané]' : currentPrompt.text);
    formData.append('region', selectedRegion.name);
    formData.append('accent', selectedRegion.accent);
    formData.append('gender', gender);
    formData.append('age', calculatedAge);
    formData.append('literacy', literacy);
    formData.append('speech_type', speechType);
    formData.append('secret_key', 'WOLOF2026');

    try {
      const response = await fetch('http://127.0.0.1:8000/api/collecte', { method: 'POST', body: formData });
      if (response.ok) {
        alert("Jërëjëf ! Enregistrement réussi.");
        if (currentPromptIdx < promptsDisponibles.length - 1) {
          setCurrentPromptIdx(currentPromptIdx + 1);
        } else {
          setCurrentPromptIdx(0);
          setStep('mode_selection');
        }
      } else {
        alert("Erreur de sauvegarde.");
      }
    } catch (error) {
      alert("Erreur de connexion avec le serveur FastAPI.");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-4 flex flex-col items-center justify-center">
      <div className="w-full max-w-md bg-slate-900 rounded-3xl shadow-2xl border border-slate-800 overflow-hidden flex flex-col p-6 space-y-6">

        {/* HEADER */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 bg-gradient-to-tr from-indigo-600 to-violet-500 rounded-2xl text-white">
              <AudioLines size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tight bg-gradient-to-r from-indigo-400 to-pink-400 bg-clip-text text-transparent">Wakhine Wolof</h1>
              <p className="text-[10px] text-slate-500 font-bold uppercase">Wakhine AI Engine</p>
            </div>
          </div>
          {step !== 'gatekeeper' && (
            <a href="http://127.0.0.1:8000/api/download-csv" download className="py-1.5 px-3 bg-slate-800 text-slate-200 text-xs font-bold rounded-xl border border-slate-700 shadow-sm">📥 CSV</a>
          )}
        </div>

        {/* ÉCRAN DE VERROUILLAGE */}
        {step === 'gatekeeper' && (
          <div className="flex flex-col space-y-5 py-4 text-center">
            <div className="mx-auto p-4 bg-indigo-500/10 text-indigo-400 rounded-full w-16 h-16 flex items-center justify-center"><Lock size={28}/></div>
            <div>
              <h2 className="text-lg font-bold">Plateforme Sécurisée de Thèse</h2>
              <p className="text-xs text-slate-400 mt-1">Veuillez saisir le code pour participer à la collecte.</p>
            </div>
            <input
              type="password"
              placeholder="Entrez le code d'accès"
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-center tracking-widest text-slate-200 focus:outline-none focus:border-indigo-500"
              value={accessCode}
              onChange={(e) => setAccessCode(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleCheckCode(); }}
            />
            <button onClick={handleCheckCode} className="w-full bg-indigo-600 hover:bg-indigo-500 font-bold py-3.5 rounded-xl transition-all flex items-center justify-center space-x-2">
              <span>Valider le code</span>
              <ArrowRight size={16}/>
            </button>
          </div>
        )}

        {/* ÉCRAN 1 : BIENVENUE */}
        {step === 'welcome' && (
          <div className="flex flex-col space-y-6 py-2">
            <p className="text-sm text-slate-400 leading-relaxed">En partageant votre voix, vous aidez à construire une intelligence artificielle qui comprend parfaitement les accents et variantes du Wolof.</p>
            <div className="space-y-4 bg-slate-950/50 rounded-2xl p-4 border border-slate-800/60">
              <div className="flex items-start space-x-3 text-sm">
                <div className="p-1.5 bg-indigo-500/10 rounded-lg text-indigo-400"><User size={16}/></div>
                <div><h4 className="font-semibold text-slate-200">Informations Personnelles</h4></div>
              </div>
              <div className="flex items-start space-x-3 text-sm">
                <div className="p-1.5 bg-purple-500/10 rounded-lg text-purple-400"><Globe2 size={16}/></div>
                <div><h4 className="font-semibold text-slate-200">Origines et Accents</h4></div>
              </div>
            </div>
            <button onClick={() => setStep('profile_identity')} className="w-full bg-indigo-600 text-white font-bold py-4 rounded-2xl flex items-center justify-center space-x-2"><span>Commencer !</span><ArrowRight size={18} /></button>
          </div>
        )}

        {/* ÉCRAN 2 : AGE & GENRE */}
        {step === 'profile_identity' && (
          <div className="flex flex-col space-y-5 py-1">
            <div className="flex items-center justify-between">
              <div><h3 className="text-lg font-bold">Informations Personnelles</h3></div>
              <span className="text-xs font-mono px-2 py-1 bg-slate-800 rounded-md text-slate-400">1/2</span>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Année de naissance</label>
                <input type="number" className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm" value={birthYear} onChange={(e) => setBirthYear(e.target.value)} />
              </div>
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Genre</label>
                <select className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm" value={gender} onChange={(e) => setGender(e.target.value)}>
                  <option value="M">Masculin</option>
                  <option value="F">Féminin</option>
                </select>
              </div>
            </div>
            <div className="flex space-x-2 pt-4">
              <button onClick={() => setStep('welcome')} className="p-3.5 bg-slate-800 rounded-xl"><ArrowLeft size={20}/></button>
              <button onClick={() => setStep('profile_origin')} className="flex-1 bg-indigo-600 font-bold p-3.5 rounded-xl flex items-center justify-center space-x-2"><span>Suivant</span><ArrowRight size={18} /></button>
            </div>
          </div>
        )}

        {/* ÉCRAN 3 : ALPHABETISATION & REGION */}
        {step === 'profile_origin' && (
          <div className="flex flex-col space-y-5 py-1">
            <div className="flex items-center justify-between">
              <div><h3 className="text-lg font-bold">Origines et Culture</h3></div>
              <span className="text-xs font-mono px-2 py-1 bg-slate-800 rounded-md text-slate-400">2/2</span>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Profil de lecture</label>
                <select className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3.5 text-sm" value={literacy} onChange={(e) => setLiteracy(e.target.value)}>
                  <option value="reader">Lecteur (Lecture de phrases)</option>
                  <option value="non_reader">Non Lecteur (Écoute-Répétition)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-bold uppercase text-slate-400 mb-1">Sélectionner votre accent régional</label>
                <div className="grid grid-cols-1 gap-2 max-h-40 overflow-y-auto pr-1 border border-slate-800 p-2 rounded-xl bg-slate-950">
                  {REGIONS_ACCENTS.map((r) => (
                    <button key={r.id} type="button" onClick={() => setSelectedRegion(r)} className={selectedRegion?.id === r.id ? "p-3 rounded-lg border text-left flex justify-between items-center border-indigo-500 bg-indigo-600/10 text-indigo-300 font-bold" : "p-3 rounded-lg border text-left flex justify-between items-center border-slate-800 bg-slate-900 text-slate-400"}>
                      <span>📍 {r.name}</span><span className="text-[10px] text-slate-500">Accent {r.accent}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
            <div className="flex space-x-2 pt-2">
              <button onClick={() => setStep('profile_identity')} className="p-3.5 bg-slate-800 rounded-xl"><ArrowLeft size={20}/></button>
              <button onClick={() => { if(!selectedRegion) { alert("Sélectionnez une région"); return; } setStep('mode_selection'); }} className="flex-1 bg-indigo-600 font-bold p-3.5 rounded-xl flex items-center justify-center space-x-2"><span>Confirmer</span><ArrowRight size={18} /></button>
            </div>
          </div>
        )}

        {/* ÉCRAN 4 : PROTOCOLES DE COLLECTE */}
        {step === 'mode_selection' && (
          <div className="flex flex-col space-y-4 py-1">
            <h2 className="text-lg font-bold">Protocoles de collecte</h2>
            <div className="grid grid-cols-1 gap-2">

              <button disabled={literacy === 'non_reader'} onClick={() => { setSpeechType('reading'); setStep('collecte'); }} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500 text-left flex items-center space-x-3 w-full disabled:opacity-30">
                <div className="p-2 bg-blue-500/10 text-blue-400 rounded-lg"><BookOpen size={18} /></div>
                <div><h4 className="font-bold text-xs">Lecture de phrases</h4></div>
              </button>

              <button onClick={() => { setSpeechType('repetition'); setStep('collecte'); }} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500 text-left flex items-center space-x-3 w-full">
                <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg"><Repeat size={18} /></div>
                <div><h4 className="font-bold text-xs">Écoute-répétition</h4></div>
              </button>

              <button onClick={() => { setSpeechType('spontaneous'); setStep('collecte'); }} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500 text-left flex items-center space-x-3 w-full">
                <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg"><MessagesSquare size={18} /></div>
                <div><h4 className="font-bold text-xs">Conversation libre</h4></div>
              </button>

              <button onClick={() => { setSpeechType('image_description'); setStep('collecte'); }} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/50 hover:border-indigo-500 text-left flex items-center space-x-3 w-full">
                <div className="p-2 bg-amber-500/10 text-amber-400 rounded-lg"><ImageIcon size={18} /></div>
                <div><h4 className="font-bold text-xs">Description d'images</h4></div>
              </button>

            </div>
            <button onClick={() => setStep('profile_origin')} className="text-xs text-slate-500 text-center underline mt-2">Retour profil</button>
          </div>
        )}

        {/* ÉCRAN 5 : ENREGISTREMENT */}
        {step === 'collecte' && (
          <div className="flex flex-col space-y-5 py-1">
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 text-center space-y-3">
              {speechType === 'repetition' && (
                <button onClick={togglePromptAudio} className="mx-auto flex items-center space-x-2 px-4 py-2 rounded-full text-white text-xs bg-indigo-600">
                  <Volume2 size={14} /><span>{isPlayingPrompt ? "Arrêter" : "Dégloul (Écouter)"}</span>
                </button>
              )}
              {speechType === 'image_description' && currentPrompt.imageUrl && (
                <img src={currentPrompt.imageUrl} alt="Support visuel" className="w-full h-28 object-cover rounded-xl border border-slate-800" />
              )}
              <p className="text-slate-200 font-medium text-base bg-slate-900/40 p-3 rounded-xl">"{currentPrompt.text}"</p>
            </div>
            <div className="flex flex-col items-center justify-center space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-[9px] uppercase font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full">Micro</span>
                {isRecording && <span className="text-xs font-mono text-rose-400 animate-pulse font-bold">{recordingDuration}s</span>}
              </div>
              {!isRecording ? (
                <button onClick={startRecording} className="w-14 h-14 rounded-full bg-emerald-500 text-slate-950 flex items-center justify-center shadow-lg"><Mic size={24} /></button>
              ) : (
                <button onClick={stopRecording} className="w-14 h-14 rounded-full bg-rose-500 text-white flex items-center justify-center shadow-lg"><Square size={20} /></button>
              )}
            </div>
            {audioUrl && (
              <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex flex-col items-center space-y-3">
                <audio src={audioUrl} controls className="w-full filter invert opacity-70 scale-90" />
                <div className="flex space-x-2 w-full">
                  <button onClick={() => { setAudioUrl(null); setAudioBlob(null); setRecordingDuration(0); }} className="flex-1 bg-slate-800 text-slate-200 p-2 rounded-xl text-xs flex items-center justify-center space-x-1"><RefreshCw size={12} /> <span>Recommencer</span></button>
                  <button onClick={validateAndNext} className="flex-1 bg-indigo-600 text-white p-2 rounded-xl text-xs font-bold flex items-center justify-center space-x-1"><CheckCircle size={12} /> <span>Woor na (Valider)</span></button>
                </div>
              </div>
            )}
            <button onClick={() => setStep('mode_selection')} className="text-xs text-slate-500 text-center underline">Changer de protocole</button>
          </div>
        )}

      </div>
    </div>
  );
}
