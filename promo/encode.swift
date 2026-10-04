// 프레임 목록(한 줄에 이미지 경로 하나, 출력 프레임 순서)을 H.264 MP4 로 묶는다 - macOS 기본 AVFoundation 만 쓴다.
// 사용: swift encode.swift <frames.txt> <out.mp4> <폭> <높이> <fps> [비트레이트(bps), 기본 6000000]
import AVFoundation
import CoreGraphics
import Foundation
import ImageIO

let a = CommandLine.arguments
let list = try! String(contentsOfFile: a[1], encoding: .utf8).split(separator: "\n").map(String.init)
let out = URL(fileURLWithPath: a[2])
let W = Int(a[3])!, H = Int(a[4])!, fps = Int32(a[5])!
let bitrate = a.count > 6 ? Int(a[6])! : 6_000_000
try? FileManager.default.removeItem(at: out)
let writer = try! AVAssetWriter(outputURL: out, fileType: .mp4)
let input = AVAssetWriterInput(mediaType: .video, outputSettings: [
  AVVideoCodecKey: AVVideoCodecType.h264, AVVideoWidthKey: W, AVVideoHeightKey: H,
  AVVideoCompressionPropertiesKey: [AVVideoAverageBitRateKey: bitrate, AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel],
])
input.expectsMediaDataInRealTime = false
let adaptor = AVAssetWriterInputPixelBufferAdaptor(assetWriterInput: input, sourcePixelBufferAttributes: [
  kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB, kCVPixelBufferWidthKey as String: W, kCVPixelBufferHeightKey as String: H,
])
writer.add(input)
writer.startWriting()
writer.startSession(atSourceTime: .zero)
var last: (String, CVPixelBuffer)? = nil
for (i, path) in list.enumerated() {
  while !input.isReadyForMoreMediaData { Thread.sleep(forTimeInterval: 0.003) }
  var pb: CVPixelBuffer
  if let c = last, c.0 == path { pb = c.1 } else {
    guard let src = CGImageSourceCreateWithURL(URL(fileURLWithPath: path) as CFURL, nil),
          let img = CGImageSourceCreateImageAtIndex(src, 0, nil) else { continue }
    var p: CVPixelBuffer?
    CVPixelBufferPoolCreatePixelBuffer(nil, adaptor.pixelBufferPool!, &p)
    pb = p!
    CVPixelBufferLockBaseAddress(pb, [])
    let ctx = CGContext(data: CVPixelBufferGetBaseAddress(pb), width: W, height: H, bitsPerComponent: 8,
                        bytesPerRow: CVPixelBufferGetBytesPerRow(pb), space: CGColorSpaceCreateDeviceRGB(),
                        bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue)!
    ctx.interpolationQuality = .high
    ctx.draw(img, in: CGRect(x: 0, y: 0, width: W, height: H))
    CVPixelBufferUnlockBaseAddress(pb, [])
    last = (path, pb)
  }
  adaptor.append(pb, withPresentationTime: CMTime(value: CMTimeValue(i), timescale: fps))
}
input.markAsFinished()
let sem = DispatchSemaphore(value: 0)
writer.finishWriting { sem.signal() }
sem.wait()
print(writer.status == .completed ? "ok \(list.count) frames" : "fail \(String(describing: writer.error))")
