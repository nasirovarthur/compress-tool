import AppKit
import CoreGraphics
import Foundation

@main
struct VBCompressE2E {
    static func main() throws {
        let root = FileManager.default.temporaryDirectory
            .appendingPathComponent("vb-compress-swift-e2e-\(UUID().uuidString)", isDirectory: true)
        let input = root.appendingPathComponent("input", isDirectory: true)
        let output = root.appendingPathComponent("output", isDirectory: true)
        try FileManager.default.createDirectory(at: input, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }

        let imageURL = input.appendingPathComponent("sample.png")
        let pdfURL = input.appendingPathComponent("sample.pdf")
        try makePNG(at: imageURL)
        try makePDF(at: pdfURL)

        let imageResult = CompressorEngine.compressImages(
            [imageURL],
            outputFolder: output,
            quality: 82,
            convertFormat: true,
            inputFilter: .all,
            outputFormat: .jpg
        ) { _, _, _ in }
        try assert(imageResult.processed == 1, "image processed count")
        try assert(imageResult.errors.isEmpty, "image errors")
        try assert(FileManager.default.fileExists(atPath: output.appendingPathComponent("sample_compressed.jpg").path), "image output")

        let pdfOptimizeResult = CompressorEngine.compressPDFs(
            [pdfURL],
            outputFolder: output,
            mode: .optimize,
            dpi: 100
        ) { _, _, _ in }
        try assert(pdfOptimizeResult.processed == 1, "pdf optimize processed count")
        try assert(pdfOptimizeResult.errors.isEmpty, "pdf optimize errors")
        try assert(FileManager.default.fileExists(atPath: output.appendingPathComponent("sample_compressed.pdf").path), "pdf optimize output")

        let pdfRasterResult = CompressorEngine.compressPDFs(
            [pdfURL],
            outputFolder: output,
            mode: .scanDpi,
            dpi: 72
        ) { _, _, _ in }
        try assert(pdfRasterResult.processed == 1, "pdf raster processed count")
        try assert(pdfRasterResult.errors.isEmpty, "pdf raster errors")
        try assert(FileManager.default.fileExists(atPath: output.appendingPathComponent("sample_compressed_2.pdf").path), "pdf raster output")

        print("swift e2e ok")
    }

    private static func makePNG(at url: URL) throws {
        guard let representation = NSBitmapImageRep(
            bitmapDataPlanes: nil,
            pixelsWide: 16,
            pixelsHigh: 16,
            bitsPerSample: 8,
            samplesPerPixel: 4,
            hasAlpha: true,
            isPlanar: false,
            colorSpaceName: .deviceRGB,
            bytesPerRow: 0,
            bitsPerPixel: 0
        ) else {
            throw TestError("Could not create bitmap")
        }

        NSGraphicsContext.saveGraphicsState()
        NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: representation)
        NSColor.white.setFill()
        NSRect(x: 0, y: 0, width: 16, height: 16).fill()
        NSColor.black.setFill()
        NSRect(x: 4, y: 4, width: 8, height: 8).fill()
        NSGraphicsContext.restoreGraphicsState()

        guard let data = representation.representation(using: .png, properties: [:]) else {
            throw TestError("Could not encode PNG")
        }
        try data.write(to: url)
    }

    private static func makePDF(at url: URL) throws {
        guard let consumer = CGDataConsumer(url: url as CFURL) else {
            throw TestError("Could not create PDF consumer")
        }
        var box = CGRect(x: 0, y: 0, width: 240, height: 180)
        guard let context = CGContext(consumer: consumer, mediaBox: &box, nil) else {
            throw TestError("Could not create PDF context")
        }
        context.beginPage(mediaBox: &box)
        context.setFillColor(NSColor.white.cgColor)
        context.fill(box)
        context.setFillColor(NSColor.black.cgColor)
        context.fill(CGRect(x: 36, y: 36, width: 80, height: 60))
        context.endPage()
        context.closePDF()
    }

    private static func assert(_ condition: Bool, _ label: String) throws {
        if !condition {
            throw TestError("Failed: \(label)")
        }
    }
}

struct TestError: LocalizedError {
    let message: String

    init(_ message: String) {
        self.message = message
    }

    var errorDescription: String? {
        message
    }
}
