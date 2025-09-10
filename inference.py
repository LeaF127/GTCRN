import argparse
import os
import time
import torch
import onnxruntime
import numpy as np
import soundfile as sf
from tqdm import tqdm
from librosa import istft

def inference(model_file, source_file, save_file, samplerate):
    if model_file.endswith(".onnx"):
        session = onnxruntime.InferenceSession(model_file, None, providers=['CPUExecutionProvider'])
    else:        
        print("check your model file is [onnx] type.")
        os._exit(0)
    
    T_list = []
    outputs = []

    x = torch.from_numpy(sf.read(source_file, dtype='float32')[0])
    x = torch.stft(x, 512, 256, 512, torch.hann_window(512).pow(0.5), return_complex=False)[None]

    conv_cache = np.zeros([2, 1, 16, 16, 33],  dtype="float32")
    tra_cache = np.zeros([2, 3, 1, 1, 16],  dtype="float32")
    inter_cache = np.zeros([2, 1, 33, 16],  dtype="float32")

    inputs = x.numpy()
    for i in tqdm(range(inputs.shape[-2])):
        tic = time.perf_counter()
        
        out_i,  conv_cache, tra_cache, inter_cache \
                = session.run([], {'mix': inputs[..., i:i+1, :],
                    'conv_cache': conv_cache,
                    'tra_cache': tra_cache,
                    'inter_cache': inter_cache})

        toc = time.perf_counter()
        T_list.append(toc-tic)
        outputs.append(out_i)

    outputs = np.concatenate(outputs, axis=2)
    enhanced = istft(outputs[...,0] + 1j * outputs[...,1], n_fft=512, hop_length=256, win_length=512, window=np.hanning(512)**0.5)
    sf.write(save_file, enhanced.squeeze(), samplerate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-model_file', '--model_file',
                        help='model with .pth type path to load model')
    parser.add_argument('-source_file', '--source_file',
                        help='path for speech file to enhance')
    parser.add_argument('-save_file', '--save_file',
                        help='path for saving enhanced speech file')
    parser.add_argument('-sr', '--sample_rate', type=int, default=16000,
                        help='sample rate')
    args = parser.parse_args()

    inference(args.model_file, args.source_file, args.save_file, args.sample_rate)
