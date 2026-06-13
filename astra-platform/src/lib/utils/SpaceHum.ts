// Elegant Space Ambient Audio Player
// Plays 'space-ambient.mp3' loop with smooth volume transitions.

export class SpaceHum {
  private audio: HTMLAudioElement | null = null;
  private isPlaying = false;
  private fadeInterval: any = null;

  constructor() {}

  private initAudio() {
    if (this.audio) return;
    this.audio = new Audio('/space-ambient.mp3');
    this.audio.loop = true;
    this.audio.volume = 0;
  }

  public start() {
    if (this.isPlaying) return;
    this.isPlaying = true;

    try {
      this.initAudio();
      if (!this.audio) return;

      if (this.fadeInterval) {
        clearInterval(this.fadeInterval);
      }

      this.audio.play().then(() => {
        const targetVolume = 0.45;
        let vol = this.audio ? this.audio.volume : 0;
        
        this.fadeInterval = setInterval(() => {
          if (!this.isPlaying || !this.audio) {
            clearInterval(this.fadeInterval);
            return;
          }
          vol += 0.03;
          if (vol >= targetVolume) {
            vol = targetVolume;
            clearInterval(this.fadeInterval);
          }
          this.audio.volume = vol;
        }, 100);
      }).catch((err) => {
        console.warn('Audio play block or load failure:', err);
      });
    } catch (err) {
      console.warn('Web Audio player failed to start:', err);
    }
  }

  public stop() {
    if (!this.isPlaying) return;
    this.isPlaying = false;

    if (this.fadeInterval) {
      clearInterval(this.fadeInterval);
    }

    if (!this.audio) return;

    try {
      let vol = this.audio.volume;
      this.fadeInterval = setInterval(() => {
        if (this.isPlaying || !this.audio) {
          clearInterval(this.fadeInterval);
          return;
        }
        vol -= 0.03;
        if (vol <= 0) {
          vol = 0;
          clearInterval(this.fadeInterval);
          this.audio.pause();
          this.audio.currentTime = 0; // reset track to start
        } else {
          this.audio.volume = vol;
        }
      }, 100);
    } catch (err) {
      console.warn('Web Audio player failed to stop:', err);
    }
  }
}

// Export singleton instance
export const spaceHumSynth = typeof window !== 'undefined' ? new SpaceHum() : null;
