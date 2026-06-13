// Elegant Space Ambient Audio Generator using Web Audio API
// Generates observatory hum, ventilation ambience, and deep-space resonance locally.

export class SpaceHum {
  private ctx: AudioContext | null = null;
  private masterGain: GainNode | null = null;
  private humOsc: OscillatorNode | null = null;
  private resOsc: OscillatorNode | null = null;
  private lfo: OscillatorNode | null = null;
  private noiseSource: AudioBufferSourceNode | null = null;
  private isPlaying = false;
  private currentVolume = 0.5;

  constructor() {}

  private init() {
    if (this.ctx) return;
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;

    this.ctx = new AudioContextClass();
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.setValueAtTime(0, this.ctx.currentTime);
    this.masterGain.connect(this.ctx.destination);

    // 1. Low frequency observatory hum (55 Hz sine wave)
    this.humOsc = this.ctx.createOscillator();
    this.humOsc.type = 'sine';
    this.humOsc.frequency.setValueAtTime(55, this.ctx.currentTime);
    const humGain = this.ctx.createGain();
    humGain.gain.setValueAtTime(0.08, this.ctx.currentTime);
    this.humOsc.connect(humGain);
    humGain.connect(this.masterGain);

    // 2. Ventilation ambience (filtered noise)
    const bufferSize = this.ctx.sampleRate * 2; // 2 seconds of noise
    const noiseBuffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
    const output = noiseBuffer.getChannelData(0);
    // Generate pink-like noise values
    let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0;
    for (let i = 0; i < bufferSize; i++) {
      const white = Math.random() * 2 - 1;
      b0 = 0.99886 * b0 + white * 0.0555179;
      b1 = 0.99332 * b1 + white * 0.0750759;
      b2 = 0.96900 * b2 + white * 0.1538520;
      b3 = 0.86650 * b3 + white * 0.3104856;
      b4 = 0.55000 * b4 + white * 0.5329522;
      b5 = -0.7616 * b5 - white * 0.0168980;
      output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
      output[i] *= 0.11; // scale to fit
      b6 = white * 0.115926;
    }
    
    this.noiseSource = this.ctx.createBufferSource();
    this.noiseSource.buffer = noiseBuffer;
    this.noiseSource.loop = true;

    const noiseFilter = this.ctx.createBiquadFilter();
    noiseFilter.type = 'bandpass';
    noiseFilter.frequency.setValueAtTime(200, this.ctx.currentTime);
    noiseFilter.Q.setValueAtTime(0.8, this.ctx.currentTime);

    const noiseGain = this.ctx.createGain();
    noiseGain.gain.setValueAtTime(0.04, this.ctx.currentTime);

    this.noiseSource.connect(noiseFilter);
    noiseFilter.connect(noiseGain);
    noiseGain.connect(this.masterGain);

    // 3. Deep-space resonance (110 Hz sine modulated by a very slow 0.08 Hz LFO)
    this.resOsc = this.ctx.createOscillator();
    this.resOsc.type = 'sine';
    this.resOsc.frequency.setValueAtTime(110, this.ctx.currentTime);

    const resGain = this.ctx.createGain();
    resGain.gain.setValueAtTime(0.03, this.ctx.currentTime);

    this.lfo = this.ctx.createOscillator();
    this.lfo.type = 'sine';
    this.lfo.frequency.setValueAtTime(0.08, this.ctx.currentTime); // very slow swell

    const lfoGain = this.ctx.createGain();
    lfoGain.gain.setValueAtTime(0.015, this.ctx.currentTime); // swell intensity

    this.lfo.connect(lfoGain);
    lfoGain.connect(resGain.gain);

    this.resOsc.connect(resGain);
    resGain.connect(this.masterGain);

    // Start all sound generators
    this.humOsc.start();
    this.noiseSource.start();
    this.resOsc.start();
    this.lfo.start();
  }

  public start() {
    this.isPlaying = true;
    try {
      this.init();
      if (!this.ctx || !this.masterGain) return;
      if (this.ctx.state === 'suspended') {
        this.ctx.resume();
      }
      // Fade in to current volume
      this.masterGain.gain.linearRampToValueAtTime(this.currentVolume, this.ctx.currentTime + 0.5);
    } catch (err) {
      console.warn('Failed to start space hum synthesizer:', err);
    }
  }

  public stop() {
    this.isPlaying = false;
    if (!this.ctx || !this.masterGain) return;
    try {
      // Fade out to 0
      this.masterGain.gain.linearRampToValueAtTime(0, this.ctx.currentTime + 0.3);
      // Wait for fade out to complete, then suspend
      setTimeout(() => {
        if (!this.isPlaying && this.ctx && this.ctx.state === 'running') {
          this.ctx.suspend();
        }
      }, 350);
    } catch (err) {
      console.warn('Failed to stop space hum synthesizer:', err);
    }
  }

  public setVolume(volume: number) {
    this.currentVolume = Math.max(0, Math.min(1, volume));
    if (this.ctx && this.masterGain && this.isPlaying) {
      this.masterGain.gain.linearRampToValueAtTime(this.currentVolume, this.ctx.currentTime + 0.1);
    }
  }
}

// Export singleton instance
export const spaceHumSynth = typeof window !== 'undefined' ? new SpaceHum() : null;
