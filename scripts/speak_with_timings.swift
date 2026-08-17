// 文を Ava の声で合成しながら、各単語の開始時刻を記録するツール
// 使い方: swift speak_with_timings.swift "文" 出力.caf 出力.json [速さ0-1]
import AVFoundation
import Foundation

let args = CommandLine.arguments
guard args.count >= 4 else {
    fputs("usage: speak_with_timings.swift <text> <out.caf> <out.json> [rate]\n", stderr)
    exit(1)
}
let text = args[1]
let outAudio = URL(fileURLWithPath: args[2])
let outJson = URL(fileURLWithPath: args[3])
let rate: Float = args.count > 4 ? (Float(args[4]) ?? 0.42) : 0.42

let voice = AVSpeechSynthesisVoice.speechVoices().first {
    $0.language == "en-US" && $0.name.contains("Ava") && $0.quality == .premium
} ?? AVSpeechSynthesisVoice.speechVoices().first {
    $0.language == "en-US" && $0.name.contains("Ava")
}
guard let voice else {
    fputs("Ava voice not found\n", stderr)
    exit(2)
}

final class Delegate: NSObject, AVSpeechSynthesizerDelegate {
    var boundaries: [(String, Double)] = []
    var frames: Int64 = 0
    var sampleRate: Double = 0
    var file: AVAudioFile?
    var done = false

    func speechSynthesizer(_ s: AVSpeechSynthesizer, willSpeakRangeOfSpeechString r: NSRange, utterance u: AVSpeechUtterance) {
        let word = (u.speechString as NSString).substring(with: r)
        let t = sampleRate > 0 ? Double(frames) / sampleRate : 0
        boundaries.append((word, t))
    }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didFinish u: AVSpeechUtterance) { done = true }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didCancel u: AVSpeechUtterance) { done = true }
}

let delegate = Delegate()
let synth = AVSpeechSynthesizer()
synth.delegate = delegate

let utt = AVSpeechUtterance(string: text)
utt.voice = voice
utt.rate = rate

synth.write(utt) { buffer in
    guard let pcm = buffer as? AVAudioPCMBuffer, pcm.frameLength > 0 else { return }
    if delegate.file == nil {
        delegate.sampleRate = pcm.format.sampleRate
        delegate.file = try? AVAudioFile(forWriting: outAudio, settings: pcm.format.settings)
    }
    try? delegate.file?.write(from: pcm)
    delegate.frames += Int64(pcm.frameLength)
}

let deadline = Date().addingTimeInterval(60)
while !delegate.done && Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
}

let total = delegate.sampleRate > 0 ? Double(delegate.frames) / delegate.sampleRate : 0
let entries: [[String: Any]] = delegate.boundaries.map { ["word": $0.0, "start": $0.1] }
let obj: [String: Any] = ["total": total, "sampleRate": delegate.sampleRate, "words": entries]
let data = try! JSONSerialization.data(withJSONObject: obj, options: [.prettyPrinted])
try! data.write(to: outJson)
print("ok total=\(total)s words=\(entries.count)")
