model_file="/work/cjh/gtcrn/stream/onnx_models/pytorch_model_simple.onnx"
source_file="/work/cjh/gtcrn/wav/test1.wav"
save_file="/work/cjh/gtcrn/test_wavs/test1_pytorch_model_simple_onnx_new.wav"

python inference.py --model_file ${model_file} \
                    --source_file ${source_file} \
                    --save_file ${save_file} \
                    --sample_rate 16000

# 多文件
# for file in $(find /work/cjh/gtcrn/testset_noisy -type f); do
#   python inference.py --model_file ${model_file} --source_file $file --save_file /tsdata/cjh/testset_gtcrn/$(basename $file) --sample_rate 16000
# done