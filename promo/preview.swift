// README 용 움직이는 미리보기 - 완성된 MP4 에서 구간을 뽑아 줄인 뒤 GIF(또는 APNG)로 쓴다. macOS 기본 AVFoundation, ImageIO 만 쓴다.
// GitHub README 는 저장소의 동영상을 재생하지 않으므로 README 에는 이 미리보기를 싣고, 누르면 전체 영상으로 간다.
// 사용: swift preview.swift <in.mp4> <out.gif|out.png> <폭> <fps> <시작초> <끝초>
import AVFoundation
import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

let a = CommandLine.arguments
let asset = AVURLAsset(url: URL(fileURLWithPath: a[1]))
let out = URL(fileURLWithPath: a[2])
let W = Int(a[3])!, fps = Double(a[4])!, t0 = Double(a[5])!, t1 = Double(a[6])!
let gif = out.pathExtension.lowercased() == "gif"
let gen = AVAssetImageGenerator(asset: asset)
gen.requestedTimeToleranceBefore = .zero
gen.requestedTimeToleranceAfter = .zero
gen.maximumSize = CGSize(width: W, height: W)
var times: [Double] = []
var t = t0
while t < t1 { times.append(t); t += 1 / fps }
let dest = CGImageDestinationCreateWithURL(out as CFURL, (gif ? UTType.gif : UTType.png).identifier as CFString, times.count, nil)!
let loop: [String: Any] = gif ? [kCGImagePropertyGIFDictionary as String: [kCGImagePropertyGIFLoopCount as String: 0]]
                              : [kCGImagePropertyPNGDictionary as String: [kCGImagePropertyAPNGLoopCount as String: 0]]
CGImageDestinationSetProperties(dest, loop as CFDictionary)
let frameProps: [String: Any] = gif ? [kCGImagePropertyGIFDictionary as String: [kCGImagePropertyGIFDelayTime as String: 1 / fps]]
                                    : [kCGImagePropertyPNGDictionary as String: [kCGImagePropertyAPNGDelayTime as String: 1 / fps]]
var n = 0
for s in times {
  if let img = try? gen.copyCGImage(at: CMTime(seconds: s, preferredTimescale: 600), actualTime: nil) {
    CGImageDestinationAddImage(dest, img, frameProps as CFDictionary)
    n += 1
  }
}
print(CGImageDestinationFinalize(dest) ? "ok \(n) frames" : "fail")
