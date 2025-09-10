import os
import time
import onnx
from onnxsim import simplify
import torch
import soundfile as sf
from gtcrn import GTCRN
from stream.modules.convert import convert_to_stream
from stream.gtcrn_stream import StreamGTCRN

source_model = "/work/cjh/gtcrn/stream/onnx_models/pytorch_model.bin"
save_model = "/work/cjh/gtcrn/stream/onnx_models/pytorch_model.onnx"

device = torch.device("cpu")

model = GTCRN().to(device).eval()
# model.load_state_dict(torch.load(source_model, map_location=device)['model'])
model.load_state_dict(torch.load(source_model, map_location=device))
stream_model = StreamGTCRN().to(device).eval()
convert_to_stream(stream_model, model)

conv_cache = torch.zeros(2, 1, 16, 16, 33).to(device)
tra_cache = torch.zeros(2, 3, 1, 1, 16).to(device)
inter_cache = torch.zeros(2, 1, 33, 16).to(device)

input = torch.randn(1, 257, 1, 2, device=device)
torch.onnx.export(stream_model,
                (input, conv_cache, tra_cache, inter_cache),
                save_model,
                input_names = ['mix', 'conv_cache', 'tra_cache', 'inter_cache'],
                output_names = ['enh', 'conv_cache_out', 'tra_cache_out', 'inter_cache_out'],
                opset_version=11,
                verbose = False)

onnx_model = onnx.load(save_model)
onnx.checker.check_model(onnx_model)

# simplify onnx model
if not os.path.exists(save_model.split('.onnx')[0]+'_simple.onnx'):
    model_simp, check = simplify(onnx_model)
    assert check, "Simplified ONNX model could not be validated"
    onnx.save(model_simp, save_model.split('.onnx')[0] + '_simple.onnx')