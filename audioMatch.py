import binascii
import os


def buildDejavu():
    import os
    import matplotlib.mlab as mlab
    import matplotlib.pyplot as plt

    from scipy.ndimage.morphology import (
        generate_binary_structure, binary_erosion, iterate_structure
    )
    import hashlib
    from operator import itemgetter
    from six.moves import range
    from six.moves import zip
    CONFIDENCE = 'confidence'
    MATCH_TIME = 'match_time'
    OFFSET = 'offset'
    IDX_FREQ_I = 0
    IDX_TIME_J = 1

    ######################################################################
    # Sampling rate, related to the Nyquist conditions, which affects
    # the range frequencies we can detect.
    DEFAULT_FS = os.getenv('DEFAULT_FS', 44100)

    ######################################################################
    # Size of the FFT window, affects frequency granularity
    DEFAULT_WINDOW_SIZE = os.getenv('DEFAULT_WINDOW_SIZE', 4096)

    ######################################################################
    # Ratio by which each sequential window overlaps the last and the
    # next window. Higher overlap will allow a higher granularity of offset
    # matching, but potentially more fingerprints.
    DEFAULT_OVERLAP_RATIO = os.getenv('DEFAULT_OVERLAP_RATIO', 0.5)

    ######################################################################
    # Degree to which a fingerprint can be paired with its neighbors --
    # higher will cause more fingerprints, but potentially better accuracy.
    DEFAULT_FAN_VALUE = os.getenv('DEFAULT_FAN_VALUE', 15)

    ######################################################################
    # Minimum amplitude in spectrogram in order to be considered a peak.
    # This can be raised to reduce number of fingerprints, but can negatively
    # affect accuracy.
    DEFAULT_AMP_MIN = os.getenv('DEFAULT_AMP_MIN', 10)

    ######################################################################
    # Number of cells around an amplitude peak in the spectrogram in order
    # for Dejavu to consider it a spectral peak. Higher values mean less
    # fingerprints and faster matching, but can potentially affect accuracy.
    PEAK_NEIGHBORHOOD_SIZE = os.getenv('PEAK_NEIGHBORHOOD_SIZE', 20)

    ######################################################################
    # Thresholds on how close or far fingerprints can be in time in order
    # to be paired as a  If your max is too low, higher values of
    # DEFAULT_FAN_VALUE may not perform as expected.
    MIN_HASH_TIME_DELTA = os.getenv('MIN_HASH_TIME_DELTA', 0)
    MAX_HASH_TIME_DELTA = os.getenv('MAX_HASH_TIME_DELTA', 200)

    ######################################################################
    # If True, will sort peaks temporally for fingerprinting;
    # not sorting will cut down number of fingerprints, but potentially
    # affect performance.
    PEAK_SORT = True

    ######################################################################
    # Number of bits to throw away from the front of the SHA1 hash in the
    # fingerprint calculation. The more you throw away, the less storage, but
    # potentially higher collisions and misclassifications when identifying songs.
    FINGERPRINT_REDUCTION = os.getenv('FINGERPRINT_REDUCTION', 20)

    def fingerprint(
            channel_samples,
            Fs=DEFAULT_FS,
            wsize=DEFAULT_WINDOW_SIZE,
            wratio=DEFAULT_OVERLAP_RATIO,
            fan_value=DEFAULT_FAN_VALUE,
            amp_min=DEFAULT_AMP_MIN
    ):
        """
        FFT the channel, log transform output, find local maxima, then return
        locally sensitive hashes.
        """
        # FFT the signal and extract frequency components
        arr2D = mlab.specgram(
            channel_samples,
            NFFT=wsize,
            Fs=Fs,
            window=mlab.window_hanning,
            noverlap=int(wsize * wratio)
        )[0]

        # apply log transform since specgram() returns linear array
        arr2D = 10 * numpy.log10(arr2D)
        arr2D[arr2D == -numpy.inf] = 0  # replace infs with zeros

        # find local maxima
        local_maxima = get_2D_peaks(arr2D, plot=False, amp_min=amp_min)

        # return hashes
        return generate_hashes(local_maxima, fan_value=fan_value)

    def get_2D_peaks(arr2D, plot=False, amp_min=DEFAULT_AMP_MIN):
        # http://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.morphology.iterate_structure.html#scipy.ndimage.morphology.iterate_structure

        struct = generate_binary_structure(2, 1)
        neighborhood = iterate_structure(struct, PEAK_NEIGHBORHOOD_SIZE)
        # find local maxima using our fliter shape
        try:
            import cupy as cp
            print('使用cupy进行特征提取')

            from cupyx.scipy.ndimage.filters import maximum_filter as maximum_filter
            local_max = cp.asnumpy(maximum_filter(cp.array(arr2D), footprint=neighborhood)) == arr2D
        except:
            print('使用scipy进行特征提取')
            from scipy.ndimage.filters import maximum_filter
            local_max = maximum_filter(arr2D, footprint=neighborhood) == arr2D

        background = (arr2D == 0)
        eroded_background = binary_erosion(
            background, structure=neighborhood, border_value=1
        )

        # Boolean mask of arr2D with True at peaks
        detected_peaks = local_max ^ eroded_background

        # extract peaks
        amps = arr2D[detected_peaks]
        j, i = numpy.where(detected_peaks)

        # filter peaks
        amps = amps.flatten()
        peaks = list(zip(i, j, amps))
        peaks_filtered = [x for x in peaks if x[2] > amp_min]  # freq, time, amp

        # get indices for frequency and time
        frequency_idx = [x[1] for x in peaks_filtered]
        time_idx = [x[0] for x in peaks_filtered]

        if plot:
            # scatter of the peaks
            fig, ax = plt.subplots()
            ax.imshow(arr2D)
            ax.scatter(time_idx, frequency_idx)
            ax.set_xlabel('Time')
            ax.set_ylabel('Frequency')
            ax.set_title("Spectrogram")
            plt.gca().invert_yaxis()
            plt.show()

        return list(zip(frequency_idx, time_idx))

    def generate_hashes(peaks, fan_value=DEFAULT_FAN_VALUE):
        """
        Hash list structure:
           sha1_hash[0:20]    time_offset
        [(e05b341a9b77a51fd26, 32), ... ]
        """
        if PEAK_SORT:
            peaks.sort(key=itemgetter(1))

        for i in range(len(peaks)):
            for j in range(1, fan_value):
                if (i + j) < len(peaks):

                    freq1 = peaks[i][IDX_FREQ_I]
                    freq2 = peaks[i + j][IDX_FREQ_I]
                    t1 = peaks[i][IDX_TIME_J]
                    t2 = peaks[i + j][IDX_TIME_J]
                    t_delta = t2 - t1

                    if t_delta >= MIN_HASH_TIME_DELTA and t_delta <= MAX_HASH_TIME_DELTA:
                        key = u"{}|{}|{}".format(freq1, freq2, t_delta)
                        h = hashlib.sha1(key.encode('utf-8'))
                        yield (h.hexdigest()[0:FINGERPRINT_REDUCTION], t1)

    def array_fingerprint_worker(channels, fps):
        result = set()
        for i in range(channels.shape[1]):
            channel = channels[:, i]
            hashes = fingerprint(channel, Fs=fps)
            result |= set(hashes)
        return result

    def align_delay(matches):
        """
            Finds hash matches that align in time with other matches and finds
            consensus about which hashes are "true" signal from the audio.

            Returns a dictionary with match information.
        """
        # align by diffs
        diff_counter = {}
        largest = 0
        largest_count = 0
        for diff in matches:
            if diff not in diff_counter:
                diff_counter[diff] = 0
            diff_counter[diff] += 1

            if diff_counter[diff] > largest_count:
                largest = diff
                largest_count = diff_counter[diff]

        # extract idenfication

        # return match info
        nseconds = round(
            float(largest) / DEFAULT_FS *
            DEFAULT_WINDOW_SIZE * DEFAULT_OVERLAP_RATIO,
            5
        )
        song = {
            CONFIDENCE: largest_count,
            # Dejavu.OFFSET: int(largest),
            'offset_seconds': nseconds,
        }
        return song

    return fingerprint, array_fingerprint_worker, align_delay, DEFAULT_OVERLAP_RATIO, DEFAULT_WINDOW_SIZE, DEFAULT_FS


fingerprint, array_fingerprint_worker, align_delay, \
DEFAULT_OVERLAP_RATIO, DEFAULT_WINDOW_SIZE, DEFAULT_FS = buildDejavu()

import json

locale = json.load(open("data/locale.json", encoding='utf-8'))

from moviepy.video.io.VideoFileClip import VideoFileClip
from moviepy.audio.io.AudioFileClip import AudioFileClip

import numpy as np
import numpy


def mPrint(*args, end='\n'):
    global initPrint
    if initPrint == False:
        open('log.txt', 'w', encoding='utf-8').close()
        initPrint = True
    open('log.txt', 'a', encoding='utf-8').write(' '.join(map(str, args)) + end)
    print(*args, end=end)


class fpath(str):

    def __new__(cls, value):
        return str.__new__(cls, value)

    def __init__(self, value):
        str.__init__(self)
        self.__spath = None
        self.__lpathslice = None

    def fatherDir(self, count=1):
        res = self
        for i in range(count):
            res = res[:max(res.rfind('/'), res.rfind('\\'))]
        return fpath(res)

    def __call__(self, *argv):
        if self.__spath is None:
            self.__spath = self.replace('\\', '/')
        if self.__lpathslice is None:
            self.__lpathslice = self.__spath.split('/')
        if len(argv) == 1:
            return fpath(self.__lpathslice[argv[0]])
        if len(argv) == 2:
            if argv[0] == argv[1]:
                return fpath(self.__lpathslice[argv[0]])
            if argv[0] < 0:
                start = len(self.__lpathslice) + argv[0]
            else:
                start = argv[0]
            if argv[1] < 0:
                stop = len(self.__lpathslice) + argv[1]
            else:
                stop = argv[1]
            return fpath('/'.join(self.__lpathslice[start:stop]))

    def __truediv__(self, rhs):

        if isinstance(rhs, fpath):
            raise ValueError(rhs, self)
        return fpath(f'{self}/{rhs}')

    def __add__(self, other):
        return fpath(str(self) + other)

    startswith = None

    def listDir(self):
        return list(map(lambda x: fpath(f'{self}/{x}'), os.listdir(self)))

    def fileList(self):
        return os.listdir(self)

    def fileName(self):
        return self[max(self.rfind('/'), self.rfind('\\')) + 1:]

    def isFile(self):
        return os.path.isfile(self)

    def isDir(self):
        return os.path.isdir(self)

    def exists(self):
        return os.path.exists(self)

    def mtime(self):
        return os.path.getmtime(self)

    def fileType(self):
        return self[self.rfind('.') + 1:]

    def textName(self):
        return self[max(self.rfind('/'), self.rfind('\\')) + 1:self.rfind('.')]

    def rename(self, name):
        nfile = self.fatherDir() / name
        os.rename(self, nfile)
        return nfile

    def delete(self):
        if self.isFile():
            os.remove(self)
        else:
            import shutil
            shutil.rmtree(self)

    def ensureDir(self):
        if not self.isDir():
            from os import makedirs
            makedirs(self)
            return False
        else:
            return True

    def subPath(self, name):
        return self / name

    def relative(self, other):
        assert other.replace('\\', '/').startswith(self.replace('\\', '/'))
        return other[self.__len__() + 1:]

    def extension(self, ext):
        return self.fatherDir() / (self.textName() + '.' + ext)

    def dump(self, obj):
        import json
        open(self, 'w', encoding='utf-8').write(json.dumps(obj, ensure_ascii=False, indent='\t'))


def warn():
    import traceback
    traceback.print_exc(file=open('log.txt', 'a', encoding='utf-8'))
    traceback.print_exc()


class VideoAudio:

    def __init__(self):
        self.oDuration = None
        self.oMapper = None
        self.olpos = None
        self.nDuration = None
        self.nMapper = None
        self.nlpos = None
        pass

    def match(self, pClipedVideo: str, pOriginVideo: str, searchAllFirst=False,
              oAudio: AudioFileClip = None, nAudio: AudioFileClip = None, biliInfo=None,
              lang="en"):

        if lang == "en":
            messages = locale.keys()
        else:
            messages = locale.values()

        pClipedVideo = fpath(pClipedVideo)
        pOriginVideo = fpath(pOriginVideo)

        print(messages[0], pClipedVideo.fileName(), '=>', pOriginVideo.fileName())

        print(messages[1])

        self.oDuration, self.oMapper = self.genHash(pOriginVideo, oAudio)
        self.olpos = self.oMapper[:, 1] / DEFAULT_FS * \
                     DEFAULT_WINDOW_SIZE * DEFAULT_OVERLAP_RATIO
        print(messages[2])
        print(messages[3])

        self.nDuration, self.nMapper = self.genHash(pClipedVideo, nAudio)
        self.nlpos = self.nMapper[:, 1] / DEFAULT_FS * \
                     DEFAULT_WINDOW_SIZE * DEFAULT_OVERLAP_RATIO
        if biliInfo is not None:
            biliInfo.update(
                {
                    'fileName': pClipedVideo.fileName(),
                    'duration': self.nDuration,
                },
            )
            mPrint(biliInfo)
        print(messages[4])
        print(messages[5])

        mPrint({'sourceFile': {
            'fileName': pOriginVideo.fileName(),
            'duration': self.oDuration,
        }, })
        mPrint()
        lResult = []
        lastOffset = 0
        step = 32
        pos = -step + 10
        midSequence = []
        while True:
            pos += step
            if searchAllFirst and pos == 10:
                clipRange = [[0, self.nDuration], [0, 3]]
            else:
                clipRange = None
            result = self.posMatch(pos, offset=lastOffset, clipRange=clipRange)
            if result is None:
                break
            if result == False:
                continue
            lResult.append(result)
            currentOffset = result['offset_seconds']

            if abs(lastOffset - currentOffset) > 1:
                mPrint('Offset Changed')
                start = pos - step
                end = pos
                midSequence.append([start, end])
            while len(midSequence) != 0:
                start, end = midSequence.pop()
                while True:
                    mid = (start + end) / 2
                    if mid - start < 1:
                        break
                    result = self.posMatch(mid, offset=lastOffset)
                    if result is None or result == False:
                        break
                    lResult.append(result)
                    if abs(result['offset_seconds'] - currentOffset) < 0.1:
                        end = mid
                    elif abs(result['offset_seconds'] - lastOffset) < 0.1:
                        start = mid
                    else:
                        midSequence.append([start, mid])
                        midSequence.append([mid, end])
                        break

            lastOffset = currentOffset
        lResult.sort(key=lambda x: x['pos'])
        nRes = [{'pos': 0, 'offset_seconds': 0}]
        for result in lResult:
            if abs(result['offset_seconds'] - nRes[-1]['offset_seconds']) > 0.1:
                nRes.append(result)

        return result

    def genHash(self, path, audioClip=None):

        if audioClip is None:
            try:
                audioClip = VideoFileClip(path).audio
            except:
                warn()
                print("Try loading", path, " as audio")
                audioClip = AudioFileClip(path)

        oCilp = self.soundArray(audioClip, 0, audioClip.duration)
        oHashes = array_fingerprint_worker(oCilp, audioClip.fps)
        oHashes = list(oHashes)
        oHashes.sort(key=lambda x: x[1])
        result = []
        for i in range(len(oHashes)):
            result.append([int.from_bytes(binascii.b2a_base64(binascii.unhexlify(oHashes[i][0])), byteorder='big'),
                           oHashes[i][1]])
        result = numpy.asarray(result)
        return audioClip.duration, result

    def soundArray(self, audio, start, end):
        if start < 0:
            start = 0
        if end > audio.duration:
            end = audio.duration
        return (audio.subclip(start, end).to_soundarray() * 32767).astype(numpy.int16)

    def clipMapper(self, pos, offset, clipRange, count):
        # if count == 5:
        #     return self.oMapper, self.nMapper

        start, end = pos + clipRange[1][0], pos + clipRange[1][1]
        nMapper = self.nMapper[numpy.searchsorted(self.nlpos, start):numpy.searchsorted(self.nlpos, end)]

        if count == 0:
            start, end = pos + offset + clipRange[0][0], pos + offset + clipRange[0][1]
        else:
            start, end = pos + offset + clipRange[0][0] * (1 + 0.5 * count), \
                         pos + offset + clipRange[0][1] * (1 + 0.5 * count)

            # startEnd =pos + offset + clipRange[0][0] * (1 + 0.5 * (count-1))+5
            # endStart=pos + offset + clipRange[0][1] * (1 + 0.5 * count)-5
            # part = [
            #
            # ]
        oMapper = self.oMapper[numpy.searchsorted(self.olpos, start):numpy.searchsorted(self.olpos, end)]

        return oMapper, nMapper

    def posMatch(self, pos, offset=0, clipRange=None, midSearch=False, count=1):

        mPrint(pos, end=':')

        if clipRange is None:
            clipRange = [[-40, 40], [0, 1]]
        result = {
            'pos': pos,
            # 'expOffset': offset,
            # 'clipRange': clipRange,
        }
        oMapper, nMapper = self.clipMapper(pos, offset, clipRange, count)
        # oMapper = self.clipMapper(self.oMapper, oStart, oEnd)
        #
        # nMapper = self.clipMapper(self.nMapper, nStart, nEnd)

        # Get an iterable of all the hashes we need
        results = []
        for nhash, nOffset in nMapper:
            arg = numpy.argwhere(oMapper[:, 0] == nhash)
            if arg.size != 0:
                for index in arg:
                    results.append(oMapper[index[0], 1] - nOffset)
        if len(results) != 0:
            result.update(align_delay(results))
            result['offset_seconds'] = result['offset_seconds']
        else:
            result['confidence'] = 0
        if result['confidence'] < 5:
            if count > 5:
                mPrint('failed until length limit')
                return False
            if pos + clipRange[1][1] > self.nDuration - 5:
                return None
            clipRange[1][1] = 1 + (count) * 3
            mPrint('Pos', pos, 'failed confidence=', result['confidence'], ' ,retry with clipLength',
                   clipRange[1][1])
            return self.posMatch(pos, offset=offset, clipRange=clipRange, count=count + 1)
        mPrint(result)
        return result
