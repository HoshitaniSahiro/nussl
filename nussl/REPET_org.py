"""
This module implements the original REpeating Pattern Extraction Technique (REPET)
algorithm, a simple method for separating the repeating background from the 
non-repeating foreground in a piece of audio mixture.

See http://music.eecs.northwestern.edu/research.php?project=repet

References:
[1] Zafar Rafii and Bryan Pardo. "Audio Separation System and Method," 
    US20130064379 A1, US 13/612,413, March 14, 2013.
[2] Zafar Rafii and Bryan Pardo. 
    "REpeating Pattern Extraction Technique (REPET): A Simple Method for Music/Voice Separation," 
    IEEE Transactions on Audio, Speech, and Language Processing, 
    Volume 21, Issue 1, pp. 71-82, January, 2013.
[3] Zafar Rafii and Bryan Pardo. 
    "A Simple Music/Voice Separation Method based on the Extraction of the Repeating Musical Structure," 
    36th International Conference on Acoustics, Speech and Signal Processing,
    Prague, Czech Republic, May 22-27, 2011.


Required packages:
1. Numpy
2. Scipy
3. Matplotlib

Required modules:
1. f_stft
2. f_istft
"""
import numpy as np
import scipy.fftpack as scifft
import matplotlib.pyplot as plt

import FftUtils

plt.interactive('True')


def repet(x, fs, specparam=None, per=None):
    """
    The repet function implements the main algorithm.
    
    Inputs:
    x: audio mixture (M by N) containing M channels and N time samples
    fs: sampling frequency of the audio signal
    specparam (optional): list containing STFT parameters including in order the window length, 
                          window type, overlap in # of samples, and # of fft points.
                          default: window length: 40 ms
                                   window type: Hamming
                                   overlap: window length/2
                                   nfft: window length
    per (optional): if includes two elements determines the range of repeating 
         period, if only one element determines the exact value of repeating period
         in seconds - default: [0.8,min(8,(length(x)/fs)/3)])
         
    Output:
    y: repeating background (M by N) containing M channels and N time samples
       (the corresponding non-repeating foreground is equal to x-y)
       
    EXAMPLE:
    x,fs,enc = wavread('mixture.wav'); 
    y = repet(np.mat(x),fs,np.array([0.8,8]))
    wavwrite(y,'background.wav',fs,enc)
    wavwrite(x-y,'foreground.wav',fs,enc)

    * Note: the 'scikits.audiolab' package is required for reading and writing 
            .wav files
    """
    raise DeprecationWarning('Don\'t get used to using this. It\'s going away soon!')

    # use the default range of repeating period and default STFT parameter values if not specified
    if specparam is None:
        winlength = int(2 ** (np.ceil(np.log2(0.04 * fs))))
        specparam = [winlength, 'Hamming', winlength / 2, winlength]
    if per is None:
        per = np.array([0.8, np.array([8, np.shape(x)[1] / 3]).min()])

        # STFT parameters
    L, win, ovp, nfft = specparam

    # HPF parameters
    fc = 100  # cutoff freqneyc (in Hz) of the high pass filter
    fc = np.ceil(float(fc) * (nfft - 1) / fs)  # cutoff freq. (in # of freq. bins)

    # compute the spectrograms of all channels
    M, N = np.shape(x)
    X = FftUtils.f_stft(np.mat(x[0, :]), nFfts=nfft, winLength=L, windowType=win, winOverlap=ovp, sampleRate=fs)[0]
    for i in range(1, M):
        Sx = FftUtils.f_stft(np.mat(x[i, :]), nFfts=nfft, winLength=L, windowType=win, winOverlap=ovp, sampleRate=fs)[0]
        X = np.dstack([X, Sx])
    V = np.abs(X)
    if M == 1:
        X = X[:, :, np.newaxis]
        V = V[:, :, np.newaxis]

    # estimate the repeating period
    per = np.ceil((per * fs + L / ovp - 1) / ovp)
    if np.size(per) == 1:
        p = per;
    elif np.size(per) == 2:
        b = beat_spec(np.mean(V ** 2, axis=2))
        plt.figure()
        plt.plot(b)
        plt.title('Beat Spectrum')
        plt.grid('on')
        plt.axis('tight')
        plt.show()
        p = rep_period(b, per)

    # separate the mixture background by masking
    y = np.zeros((M, N))
    for i in range(0, M):
        RepMask = rep_mask(V[:, :, i], p)
        RepMask[1:fc, :] = 1  # high-pass filter the foreground
        XMi = RepMask * X[:, :, i]
        yi = FftUtils.f_istft(XMi, L, win, ovp, fs)[0]
        y[i, :] = yi[0:N]

    return y


def beat_spec(X):
    """
    The ComputeBeatSpectrum function computes the beat spectrum, which is the average (over freq.s)
    of the autocorrelation matrix of a one-sided spectrogram. The autocorrelation
    matrix is computed by taking the autocorrelation of each row of the spectrogram
    and dismissing the symmetric half.
    
    Input:
    X: 2D matrix containing the one-sided power spectrogram of the audio signal (Lf by Lt)
    Output:
    b: beat spectrum
    """
    # compute the row-wise autocorrelation of the input spectrogram
    Lf, Lt = np.shape(X)
    X = np.hstack([X, np.zeros((Lf, Lt))])
    Sx = np.abs(scifft.fft(X, axis=1) ** 2)  # fft over columns (take the fft of each row at a time)
    Rx = np.real(scifft.ifft(Sx, axis=1)[:, 0:Lt])  # ifft over columns
    NormFactor = np.tile(np.arange(1, Lt + 1)[::-1], (Lf, 1))  # normalization factor
    Rx = Rx / NormFactor

    # compute the beat spectrum
    b = np.mean(Rx, axis=0)  # average over frequencies

    return b


def rep_period(b, r):
    """
    The FindRepeatingPeriod function computes the repeating period of the sound signal
    using the beat spectrum calculated from the spectrogram.
    
    Inputs:
    b: beat spectrum
    r: array of length 2 including minimum and maximum possible period values
    Output:
    p: repeating period 
    """
    b = b[1:]  # discard the first element of b (lag 0)
    b = b[r[0] - 1:r[1]]
    p = np.argmax(b) + r[0]  ######## not sure about this part

    return p


def rep_mask(V, p):
    """
    The ComputeRepeatingMaskSim function computes the soft mask for the repeating part using
    the magnitude spectrogram and the repeating period
    
    Inputs:
    V: 2D matrix containing the magnitude spectrogram of a signal (Lf by Lt)
    p: repeating period measured in # of time frames
    Output:
    M: 2D matrix (Lf by Lt) containing the soft mask for the repeating part, 
       elements of M take on values in [0,1]
    """

    [Lf, Lt] = np.shape(V)
    r = np.ceil(float(Lt) / p)
    W = np.hstack([V, float('nan') * np.zeros((Lf, r * p - Lt))])
    W = np.reshape(W.T, (r, Lf * p))
    W1 = np.median(W[0:r, 0:Lf * (Lt - (r - 1) * p)], axis=0)
    W2 = np.median(W[0:r - 1, Lf * (Lt - (r - 1) * p):Lf * p], axis=0)
    W = np.hstack([W1, W2])
    W = np.reshape(np.tile(W, (r, 1)), (r * p, Lf)).T
    W = W[:, 0:Lt]

    Wrow = np.reshape(W, (1, Lf * Lt))
    Vrow = np.reshape(V, (1, Lf * Lt))
    W = np.min(np.vstack([Wrow, Vrow]), axis=0)
    W = np.reshape(W, (Lf, Lt))
    M = (W + 1e-16) / (V + 1e-16)

    return M
