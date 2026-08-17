// 発音記号(IPA)を指定して Ava の声で音を合成するツール(フォニックスの1音ずつの音声用)
// 使い方: swift speak_ipa.swift <表示用テキスト> <IPA> <出力.caf> [速さ0-1]
import AVFoundation
import Foundation

let args = CommandLine.arguments
guard args.count >= 4 else {
    fputs("usage: speak_ipa.swift <text> <ipa> <out.caf> [rate]\n", stderr)
    exit(1)
}
let text = args[1]
let ipa = args[2]
let outAudio = URL(fileURLWithPath: args[3])
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
    var done = false
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didFinish u: AVSpeechUtterance) { done = true }
    func speechSynthesizer(_ s: AVSpeechSynthesizer, didCancel u: AVSpeechUtterance) { done = true }
}

let delegate = Delegate()
let synth = AVSpeechSynthesizer()
synth.delegate = delegate

let attributed = NSMutableAttributedString(string: text)
attributed.addAttribute(
    NSAttributedString.Key(AVSpeechSynthesisIPANotationAttribute),
    value: ipa,
    range: NSRange(location: 0, length: attributed.length))
let utt = AVSpeechUtterance(attributedString: attributed)
utt.voice = voice
utt.rate = rate

var file: AVAudioFile?
var frames: Int64 = 0
var sampleRate: Double = 0

synth.write(utt) { buffer in
    guard let pcm = buffer as? AVAudioPCMBuffer, pcm.frameLength > 0 else { return }
    if file == nil {
        sampleRate = pcm.format.sampleRate
        file = try? AVAudioFile(forWriting: outAudio, settings: pcm.format.settings)
    }
    try? file?.write(from: pcm)
    frames += Int64(pcm.frameLength)
}

let deadline = Date().addingTimeInterval(30)
while !delegate.done && Date() < deadline {
    RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.05))
}

let total = sampleRate > 0 ? Double(frames) / sampleRate : 0
print("ok total=\(total)s")
