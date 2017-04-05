import os
import nussl


def main():
    # Load input file
    input_file_name = os.path.join('..', 'Input', 'dev1_female3_inst_mix.wav')
    signal = nussl.AudioSignal(path_to_input_file=input_file_name)

    # make a directory to store output if needed
    if not os.path.exists(os.path.join('..', 'Output/')):
        os.mkdir(os.path.join('..', 'Output/'))

    nussl.USE_LIBROSA_STFT = False
    # Set up DUET
    duet = nussl.Duet(signal, num_sources=3)

    # and run
    duet.run()

    # plot histogram results
    duet.plot(os.path.join('..', 'Output', 'duet_2d.png'))
    duet.plot(os.path.join('..', 'Output', 'duet_3d.png'), three_d_plot=True)

    # Create output file for each source found
    output_name_stem = os.path.join('..', 'Output', 'duet_source')
    i = 1
    for s in duet.make_audio_signals():
        output_file_name = output_name_stem + str(i) + '.wav'
        s.write_audio_to_file(output_file_name)
        i += 1


if __name__ == '__main__':
    main()
