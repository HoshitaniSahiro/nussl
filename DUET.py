"""
This module implements the Degenerate Unmixing Estimation Technique (DUET) algorithm.
The DUET algorithm was originally proposed by S.Rickard and F.Dietrich for DOA estimation
and further developed for BSS and demixing by A.Jourjine, S.Rickard, and O. Yilmaz.

References:
[1] Rickard, Scott. "The DUET blind source separation algorithm." Blind Speech Separation. 
    Springer Netherlands, 2007. 217-241.
[2] Yilmaz, Ozgur, and Scott Rickard. "Blind separation of speech mixtures via 
    time-frequency masking." Signal Processing, IEEE transactions on 52.7 
    (2004): 1830-1847.

Required packages:
1. Numpy
2. Scipy
3. Matplotlib

Required modules:
1. f_stft
2. f_istft
"""

import numpy as np
from FftUtils import f_stft
from f_istft import f_istft
import matplotlib.pyplot as plt

plt.interactive('True')
from scipy import signal
from mpl_toolkits.mplot3d import axes3d


def duet(x, sparam, adparam, Pr, plothist='y'):
    """
    The 'duet' function extracts N sources from a given stereo audio mixture 
    (N sources captured via 2 sensors)
    
    Inputs:
    x: a 2-row Numpy matrix containing samples of the two-channel mixture
    sparam: structure array containing spectrogram parameters including 
            L: window length (in # of samples)
          win: window type, string ('Rectangular', 'Hamming', 'Hanning', 'Blackman')
          ovp: number of overlapping samples between adjacent windows      
          nfft: min number of desired freq. samples in (-pi,pi]. MUST be >= L. 
               *NOTE* If this is not a power of 2, then it will automatically 
               zero-pad up to the next power of 2. IE if you put 257 here, 
               it will pad up to 512.
           fs: sampling rate of the signal
           ** sparam = np.array([(L,win,ovp,nfft,fs)]
           dtype=[('winlen',int),('wintype','|S10'),('overlap',int),('numfreq',int),('sampfreq',int)])
           
    adparam: structure array containing ranges and number of bins for attenuation and delay 
           ** adparam = np.array([(a_min,a_max,a_num,d_min,d_max,d_num)],
           dtype=[('amin',float),('amax',float),('anum',float),('dmin',float)
           ,('dmax',float),('dnum',int)])
    
    Pr: vector containing user defined information including a threshold value (in [0,1])
        for peak picking (thr), minimum distance between peaks, and the number of sources (N) 
        ** Pr = np.array(thr,a_mindist,d_mindist,N)
    plothist: (optional) string input, indicates if the histogram is to be plotted
          'y' (default): plot the histogram, 'n': don't plot    
          
    Output:
    xhat: an N-row Numpy matrix containing N time-domain estimates of sources
    ad_est: N by 2 Numpy matrix containing estimated attenuation and delay values
          corresponding to N sources   
    """
    # Extract the parameters from inputs
    sparam = sparam.view(np.recarray)
    adparam = adparam.view(np.recarray)
    L = sparam.winlen;
    win = sparam.wintype;
    ovp = sparam.overlap;
    nfft = sparam.numfreq;
    fs = sparam.sampfreq
    a_min = adparam.amin;
    a_max = adparam.amax;
    a_num = adparam.anum
    d_min = adparam.dmin;
    d_max = adparam.dmax;
    d_num = adparam.dnum

    thr, N, mindist = Pr[0:3]

    # Compute the STFT of the two channel mixtures
    X1, P1, F, T = f_stft(x[0, :], L, win, ovp, fs, nfft, 0)
    X2, P2, F, T = f_stft(x[1, :], L, win, ovp, fs, nfft, 0)
    # remove dc component to avoid dividing by zero freq. in the delay estimation
    X1 = X1[1::, :];
    X2 = X2[1::, :]
    Lf = len(F);
    Lt = len(T)

    # Compute the freq. matrix for later use in phase calculations
    wmat = np.array(np.tile(np.mat(F[1::]).T, (1, Lt))) * (2 * np.pi / fs)

    # Calculate the symmetric attenuation (alpha) and delay (delta) for each 
    # time-freq. point
    R21 = (X2 + 1e-16) / (X1 + 1e-16)
    atn = np.abs(R21)  # relative attenuation between the two channels
    alpha = atn - 1 / atn  # symmetric attenuation
    delta = -np.imag(np.log(R21)) / (2 * np.pi * wmat)  # relative delay

    # calculate the weighted histogram
    p = 1;
    q = 0
    tfw = (np.abs(X1) * np.abs(X2)) ** p * (np.abs(wmat)) ** q  # time-freq weights

    # only consider time-freq. points yielding estimates in bounds
    a_premask = np.logical_and(a_min < alpha, alpha < a_max)
    d_premask = np.logical_and(d_min < delta, delta < d_max)
    ad_premask = np.logical_and(a_premask, d_premask)

    ad_nzind = np.nonzero(ad_premask)
    alpha_vec = alpha[ad_nzind]
    delta_vec = delta[ad_nzind]
    tfw_vec = tfw[ad_nzind]

    # compute the histogram
    H = np.histogram2d(alpha_vec, delta_vec, bins=np.array([a_num[0], d_num[0]]),
                       range=np.array([[a_min, a_max], [d_min, d_max]]), normed=False, weights=tfw_vec)

    hist = H[0] / H[0].max()
    agrid = H[1]
    dgrid = H[2]

    # smooth the histogram - local average 3-by-3 neightboring bins 
    hist = twoDsmooth(hist, 3)

    # normalize and plot the histogram
    hist = hist / hist.max()

    if plothist == 'y':
        # plot the histogram in 2D and 3D spaces
        AA = np.tile(agrid[1::], (d_num, 1)).T
        DD = np.tile(dgrid[1::].T, (a_num, 1))
        fig = plt.figure()
        plt.pcolormesh(AA, DD, hist)
        plt.xlabel(r'$\alpha$', fontsize=16)
        plt.ylabel(r'$\delta$', fontsize=16)
        plt.title(r'$\alpha-\delta$ Histogram')
        plt.axis('tight')
        plt.show()

        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        ax.plot_wireframe(AA, DD, hist, rstride=2, cstride=2)
        plt.xlabel(r'$\alpha$', fontsize=16)
        plt.ylabel(r'$\delta$', fontsize=16)
        plt.title(r'$\alpha-\delta$ Histogram')
        plt.axis('tight')
        ax.view_init(30, 30)
        plt.draw()


    # find the location of peaks in the alpha-delta plane
    thr = Pr[0]
    min_dist = Pr[1:3]
    N = int(Pr[3])
    pindex = find_peaks2(hist, thr, min_dist, N)

    alphapeak = agrid[pindex[0, :]]
    deltapeak = dgrid[pindex[1, :]]

    ad_est = np.vstack([alphapeak, deltapeak]).T

    # convert alpha to a
    atnpeak = (alphapeak + np.sqrt(alphapeak ** 2 + 4)) / 2

    # compute masks for separation
    bestsofar = np.inf * np.ones((Lf - 1, Lt))
    bestind = np.zeros((Lf - 1, Lt), int)
    for i in range(0, N):
        score = np.abs(atnpeak[i] * np.exp(-1j * wmat * deltapeak[i]) * X1 - X2) ** 2 / (1 + atnpeak[i] ** 2)
        mask = (score < bestsofar)
        bestind[mask] = i
        bestsofar[mask] = score[mask]

    # demix with ML alignment and convert to time domain    
    Lx = np.shape(x)[1]
    xhat = np.zeros((N, Lx))
    for i in range(0, N):
        mask = (bestind == i)
        Xm = np.vstack([np.zeros((1, Lt)), (X1 + atnpeak[i] * np.exp(1j * wmat * deltapeak[i]) * X2)
                        / (1 + atnpeak[i] ** 2) * mask])
        xi = f_istft(Xm, L, win, ovp, fs)

        xhat[i, :] = np.array(xi)[0, 0:Lx]
        # add back to the separated signal a portion of the mixture to eliminate
        # most of the masking artifacts
        # xhat=xhat+0.05*x[0,:]

    return xhat, ad_est


def twoDsmooth(Mat, Kernel):
    """
    The 'twoDsmooth' function receivees a matrix and a kernel type and performes
    two-dimensional convolution in order to smooth the values of matrix elements.
    (similar to low-pass filtering)
    
    Inputs:
    Mat: a 2D Numpy matrix to be smoothed 
    Kernel: a 2D Numpy matrix containing kernel values
           Note: if Kernel is of size 1 by 1 (scalar), a Kernel by Kernel matrix
           of 1/Kernel**2 will be used as teh matrix averaging kernel
    Output:
    SMat: a 2D Numpy matrix containing a smoothed version of Mat (same size as Mat)                 
    """

    # check the dimensions of the Kernel matrix and set the values of the averaging
    # matrix, Kmat
    if np.prod(np.shape(Kernel)) == 1:
        Kmat = np.ones((Kernel, Kernel)) / Kernel ** 2
    else:
        Kmat = Kernel

    # make Kmat have odd dimensions
    krow, kcol = np.shape(Kmat)
    if np.mod(krow, 2) == 0:
        Kmat = signal.convolve2d(Kmat, np.ones((2, 1))) / 2
        krow = krow + 1

    if np.mod(kcol, 2) == 0:
        Kmat = signal.convolve2d(Kmat, np.ones((1, 2))) / 2
        kcol = kcol + 1

    # adjust the matrix dimension for convolution
    matrow, matcol = np.shape(Mat)
    copyrow = int(np.floor(krow / 2))  # number of rows to copy on top and bottom
    copycol = int(np.floor(kcol / 2))  # number of columns to copy on either side

    # form the augmented matrix (rows and columns added to top, botoom, and sides)
    Mat = np.mat(Mat)  # make sure Mat is a Numpy matrix
    augMat = np.vstack([np.hstack([Mat[0, 0] * np.ones((copyrow, copycol)), np.ones((copyrow, 1)) * Mat[0, :],
                                   Mat[0, -1] * np.ones((copyrow, copycol))])
                           , np.hstack([Mat[:, 0] * np.ones((1, copycol)), Mat, Mat[:, -1] * np.ones((1, copycol))])
                           , np.hstack([Mat[-1, 1] * np.ones((copyrow, copycol)), np.ones((copyrow, 1)) * Mat[-1, :],
                                        Mat[-1, -1] * np.ones((copyrow, copycol))])])

    # perform two-dimensional convolution between the input matrix and the kernel
    SMAT = signal.convolve2d(augMat, Kmat[::-1, ::-1], mode='valid')

    return SMAT


def find_peaks2(data, min_thr=0.5, min_dist=None, max_num=1):
    """
    The 'find_peaks2d' function receives a matrix of positive numerical 
    values (in [0,1]) and finds the peak values and corresponding indices.
    
    Inputs: 
    data: a 2D Numpy matrix containing real values (in [0,1])
    min_thr:(optional) minimum threshold (in [0,1]) on data values - default=0.5
    min_dist:(optional) 1 by 2 matrix containing minimum distances (in # of time elements) between peaks
              row-wise and column-wise - default: 25% of matrix dimensions
    max_num: (optional) maximum number of peaks in the whole matrix - default: 1
    
    Output:
    Pi: a two-row Numpy matrix containing peaks indices
    """

    # make sure data is a Numpy matrix
    data = np.mat(data)

    Rdata, Cdata = np.shape(data)
    if min_dist is None:
        min_dist = np.array([np.floor(Rdata / 4), np.floor(Cdata / 4)])

    Pi = np.zeros((2, max_num), int)
    Rmd, Cmd = min_dist.astype(int)


    # keep only the values that pass the threshold
    data = data * (data >= min_thr)

    if np.size(np.nonzero(data)) < max_num:
        raise ValueError('not enough number of peaks! change parameters.')
    else:
        i = 0
        while i < int(max_num):
            Pi[:, i] = np.unravel_index(data.argmax(), data.shape)
            data[Pi[0, i] - Rmd - 1:Pi[0, i] + Rmd + 1, Pi[1, i] - Cmd - 1:Pi[1, i] + Cmd + 1] = 0
            i = i + 1
            if np.sum(data) == 0:
                break

    return Pi


def find_peaks(data, min_thr=0.5, min_dist=None, max_num=1):
    """
    The 'FindPeaks' function receives a row vector array of positive numerical
    values (in [0,1]) and finds the peak values and corresponding indices.
    
    Inputs: 
    data: row vector of real values (in [0,1])
    min_thr: (optional) minimum threshold (in [0,1]) on data values - default=0.5
    min_dist:(optiotnal) minimum distance (in # of time elements) between peaks 
             default: 25% of the vector length
    max_num: (optional) maximum number of peaks - default: 1
    
    Output:
    Pi: peaks indices
    """

    # make sure data is a Numpy matrix
    data = np.mat(data)

    lenData = np.shape(data)[1]
    if min_dist is None:
        min_dist = np.floor(lenData / 4)

    Pi = np.zeros((1, max_num), int)

    data = np.multiply(data, (data >= min_thr))
    if np.size(np.nonzero(data)) < max_num:
        raise ValueError('not enough number of peaks! change parameters.')
    else:
        i = 0
        while i < max_num:
            Pi[0, i] = np.argmax(data)
            data[0, Pi[0, i] - min_dist - 1:Pi[0, i] + min_dist + 1] = 0
            i = i + 1
            if np.sum(data) == 0:
                break

    Pi = np.sort(Pi)

    return Pi
