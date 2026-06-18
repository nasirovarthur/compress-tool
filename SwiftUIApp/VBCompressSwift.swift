import AppKit
import CoreGraphics
import ImageIO
import PDFKit
import SwiftUI
import UniformTypeIdentifiers

private enum AppTheme {
    static let appBackground = Color(red: 0.96, green: 0.96, blue: 0.96)
    static let sidebarBackground = Color(red: 0.92, green: 0.92, blue: 0.93)
    static let cardBackground = Color.white
    static let rowText = Color(red: 0.12, green: 0.12, blue: 0.13)
    static let secondaryText = Color(red: 0.42, green: 0.42, blue: 0.45)
    static let border = Color.black.opacity(0.10)
    static let buttonBackground = Color.black.opacity(0.055)
    static let blue = Color.accentColor
}

enum WorkMode: String, CaseIterable, Identifiable {
    case images = "Images"
    case pdf = "PDF"

    var id: String { rawValue }

    var title: String { rawValue }
    var importTitle: String { self == .images ? "Import images" : "Import PDFs" }
    var importSubtitle: String {
        self == .images
            ? "Drop image files or folders here. Supported formats: JPG, PNG, WEBP."
            : "Drop PDF documents here. Folders are ignored for PDF import."
    }
}

enum ImageFormat: String, CaseIterable, Identifiable {
    case all = "All"
    case png = "PNG"
    case jpg = "JPG"
    case webp = "WEBP"

    var id: String { rawValue }
    var fileExtension: String? {
        switch self {
        case .all:
            return nil
        case .png:
            return "png"
        case .jpg:
            return "jpg"
        case .webp:
            return "webp"
        }
    }
}

enum PdfMode: String, CaseIterable, Identifiable {
    case optimize = "Optimize"
    case scanDpi = "Scan DPI"

    var id: String { rawValue }
}

struct JobError: Identifiable {
    let id = UUID()
    let fileName: String
    let message: String
}

struct JobResult {
    var processed = 0
    var skipped = 0
    var errors: [JobError] = []
}

@MainActor
final class AppModel: ObservableObject {
    @Published var mode: WorkMode = .images
    @Published var imageFiles: [URL] = []
    @Published var pdfFiles: [URL] = []
    @Published var imageQuality = 80.0
    @Published var convertFormat = false
    @Published var inputFormat: ImageFormat = .all
    @Published var outputFormat: ImageFormat = .webp
    @Published var pdfMode: PdfMode = .optimize
    @Published var pdfDpi = 100.0
    @Published var imageOutputFolder = AppModel.defaultOutputFolder("Images")
    @Published var pdfOutputFolder = AppModel.defaultOutputFolder("PDF")
    @Published var isRunning = false
    @Published var progress = 0.0
    @Published var statusText = "Ready"
    @Published var recentErrors: [JobError] = []
    @Published var isDropTargeted = false

    var activeCount: Int {
        mode == .images ? imageFiles.count : pdfFiles.count
    }

    var activeOutputFolder: URL {
        mode == .images ? imageOutputFolder : pdfOutputFolder
    }

    static func defaultOutputFolder(_ name: String) -> URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Documents", isDirectory: true)
            .appendingPathComponent("VB Compress", isDirectory: true)
            .appendingPathComponent(name, isDirectory: true)
    }

    func chooseActiveFiles() {
        mode == .images ? chooseImages() : choosePDFs()
    }

    func chooseImages() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowedContentTypes = [.png, .jpeg, .webP]
        if panel.runModal() == .OK {
            imageFiles = collectImages(from: panel.urls)
            mode = .images
            statusText = imageFiles.isEmpty ? "No image files selected" : "\(imageFiles.count) image files selected"
        }
    }

    func choosePDFs() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowedContentTypes = [.pdf]
        if panel.runModal() == .OK {
            pdfFiles = collectPDFs(from: panel.urls)
            mode = .pdf
            statusText = pdfFiles.isEmpty ? "No PDF files selected" : "\(pdfFiles.count) PDF files selected"
        }
    }

    func chooseOutputFolder(for mode: WorkMode) {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url {
            if mode == .images {
                imageOutputFolder = url
            } else {
                pdfOutputFolder = url
            }
        }
    }

    func resetActiveQueue() {
        guard !isRunning else { return }
        if mode == .images {
            imageFiles = []
            progress = 0
            statusText = "Image queue cleared"
        } else {
            pdfFiles = []
            progress = 0
            statusText = "PDF queue cleared"
        }
        recentErrors = []
    }

    func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        guard !isRunning else { return false }
        var didLoad = false
        for provider in providers where provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { [weak self] item, _ in
                guard let self else { return }
                guard let url = Self.url(fromDropItem: item) else { return }
                Task { @MainActor in
                    self.importDroppedURLs([url])
                }
            }
            didLoad = true
        }
        return didLoad
    }

    func importDroppedURLs(_ urls: [URL]) {
        if mode == .images {
            imageFiles = merge(imageFiles, collectImages(from: urls))
            statusText = imageFiles.isEmpty ? "No supported images found" : "\(imageFiles.count) image files selected"
        } else {
            pdfFiles = merge(pdfFiles, collectPDFs(from: urls))
            statusText = pdfFiles.isEmpty ? "No supported PDFs found" : "\(pdfFiles.count) PDF files selected"
        }
    }

    func runActiveJob() {
        guard !isRunning else { return }
        mode == .images ? runImageJob() : runPDFJob()
    }

    private func runImageJob() {
        guard !imageFiles.isEmpty else {
            statusText = "Select images first"
            return
        }
        let files = imageFiles
        let folder = imageOutputFolder
        let quality = imageQuality
        let shouldConvert = convertFormat
        let inputFilter = inputFormat
        let targetFormat = outputFormat
        startJob()

        Task.detached {
            let result = CompressorEngine.compressImages(
                files,
                outputFolder: folder,
                quality: quality,
                convertFormat: shouldConvert,
                inputFilter: inputFilter,
                outputFormat: targetFormat
            ) { done, total, file in
                Task { @MainActor in
                    self.progress = total == 0 ? 0 : Double(done) / Double(total)
                    self.statusText = "\(done)/\(total) \(file.lastPathComponent)"
                }
            }
            await MainActor.run {
                self.finishJob(result, label: "image files")
            }
        }
    }

    private func runPDFJob() {
        guard !pdfFiles.isEmpty else {
            statusText = "Select PDFs first"
            return
        }
        let files = pdfFiles
        let folder = pdfOutputFolder
        let mode = pdfMode
        let dpi = pdfDpi
        startJob()

        Task.detached {
            let result = CompressorEngine.compressPDFs(
                files,
                outputFolder: folder,
                mode: mode,
                dpi: dpi
            ) { done, total, file in
                Task { @MainActor in
                    self.progress = total == 0 ? 0 : Double(done) / Double(total)
                    self.statusText = "\(done)/\(total) \(file.lastPathComponent)"
                }
            }
            await MainActor.run {
                self.finishJob(result, label: "PDF files")
            }
        }
    }

    private func startJob() {
        isRunning = true
        progress = 0
        statusText = "Running"
        recentErrors = []
    }

    private func finishJob(_ result: JobResult, label: String) {
        isRunning = false
        progress = result.processed > 0 ? 1 : 0
        recentErrors = result.errors
        if result.errors.isEmpty {
            statusText = "Processed \(result.processed) \(label)"
        } else {
            statusText = "Processed \(result.processed), \(result.errors.count) errors"
        }
    }

    private func collectImages(from urls: [URL]) -> [URL] {
        collectFiles(from: urls, extensions: ["png", "jpg", "jpeg", "webp"], recursiveDirectories: true)
    }

    private func collectPDFs(from urls: [URL]) -> [URL] {
        collectFiles(from: urls, extensions: ["pdf"], recursiveDirectories: false)
    }

    private func collectFiles(from urls: [URL], extensions: Set<String>, recursiveDirectories: Bool) -> [URL] {
        var result: [URL] = []
        var seen = Set<URL>()
        for url in urls {
            var isDirectory: ObjCBool = false
            if FileManager.default.fileExists(atPath: url.path, isDirectory: &isDirectory), isDirectory.boolValue {
                guard recursiveDirectories,
                      let enumerator = FileManager.default.enumerator(
                          at: url,
                          includingPropertiesForKeys: [.isRegularFileKey],
                          options: [.skipsHiddenFiles]
                      ) else {
                    continue
                }
                for case let file as URL in enumerator where extensions.contains(file.pathExtension.lowercased()) {
                    if seen.insert(file.standardizedFileURL).inserted {
                        result.append(file)
                    }
                }
            } else if extensions.contains(url.pathExtension.lowercased()) {
                if seen.insert(url.standardizedFileURL).inserted {
                    result.append(url)
                }
            }
        }
        return result.sorted { $0.lastPathComponent.localizedCaseInsensitiveCompare($1.lastPathComponent) == .orderedAscending }
    }

    private func merge(_ current: [URL], _ incoming: [URL]) -> [URL] {
        var merged = current
        var seen = Set(current.map { $0.standardizedFileURL })
        for url in incoming where seen.insert(url.standardizedFileURL).inserted {
            merged.append(url)
        }
        return merged
    }

    nonisolated private static func url(fromDropItem item: NSSecureCoding?) -> URL? {
        if let url = item as? URL {
            return url
        }
        if let data = item as? Data {
            return URL(dataRepresentation: data, relativeTo: nil)
        }
        if let string = item as? String {
            return URL(string: string)
        }
        return nil
    }
}

struct ContentView: View {
    @StateObject private var model = AppModel()

    var body: some View {
        HStack(spacing: 0) {
            SidebarView(model: model)
                .frame(width: 248)

            Divider()

            SettingsDetailView(model: model)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .preferredColorScheme(.light)
        .frame(minWidth: 820, minHeight: 620)
        .background(AppTheme.appBackground)
    }
}

struct SidebarView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack(spacing: 10) {
                Image(nsImage: NSImage(named: "AppIcon") ?? NSImage())
                    .resizable()
                    .frame(width: 30, height: 30)
                    .clipShape(RoundedRectangle(cornerRadius: 7))

                VStack(alignment: .leading, spacing: 2) {
                    Text("VB Compress")
                        .font(.headline)
                    Text("Local optimizer")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 12)

            VStack(spacing: 4) {
                SidebarButton(
                    title: "Images",
                    subtitle: "\(model.imageFiles.count) selected",
                    icon: "photo.on.rectangle",
                    isSelected: model.mode == .images
                ) {
                    model.mode = .images
                    model.statusText = "Ready"
                }

                SidebarButton(
                    title: "PDF",
                    subtitle: "\(model.pdfFiles.count) selected",
                    icon: "doc.richtext",
                    isSelected: model.mode == .pdf
                ) {
                    model.mode = .pdf
                    model.statusText = "Ready"
                }
            }

            Spacer()

            VStack(alignment: .leading, spacing: 6) {
                Label("Processing stays local", systemImage: "lock")
                    .font(.caption)
                    .foregroundStyle(.secondary)
                Text("Images use ImageIO. PDFs use PDFKit and CoreGraphics.")
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .fixedSize(horizontal: false, vertical: true)
            }
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(nsColor: .controlBackgroundColor), in: RoundedRectangle(cornerRadius: 12))
        }
        .padding(16)
        .background(AppTheme.sidebarBackground)
    }
}

struct SidebarButton: View {
    let title: String
    let subtitle: String
    let icon: String
    let isSelected: Bool
    let action: () -> Void
    @Environment(\.isEnabled) private var isEnabled

    var body: some View {
        Button(action: action) {
            HStack(spacing: 10) {
                Image(systemName: icon)
                    .font(.system(size: 15, weight: .regular))
                    .foregroundStyle(.secondary)
                    .frame(width: 22)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.callout.weight(.medium))
                    Text(subtitle)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 9)
            .opacity(isEnabled ? 1 : 0.55)
            .background(isSelected ? Color.black.opacity(0.08) : Color.clear)
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
    }
}

struct SettingsDetailView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        GeometryReader { geometry in
            VStack(alignment: .leading, spacing: 0) {
                HeaderView(model: model, availableWidth: geometry.size.width)

                ScrollView {
                    VStack(spacing: 24) {
                        DropAreaView(model: model)

                        if model.mode == .images {
                            ImageSettingsView(model: model)
                        } else {
                            PDFSettingsView(model: model)
                        }

                        StatusSection(model: model)
                    }
                    .frame(maxWidth: 760, alignment: .topLeading)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .padding(.horizontal, adaptiveHorizontalPadding(width: geometry.size.width))
                    .padding(.top, 14)
                    .padding(.bottom, 28)
                }
                ActionFooter(model: model)
            }
            .background(AppTheme.appBackground)
        }
    }

    private func adaptiveHorizontalPadding(width: CGFloat) -> CGFloat {
        width < 620 ? 18 : 28
    }
}

struct HeaderView: View {
    @ObservedObject var model: AppModel
    let availableWidth: CGFloat

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Button {
                model.statusText = "Ready"
            } label: {
                Label("Back", systemImage: "chevron.left")
                    .font(.callout)
            }
            .buttonStyle(.plain)
            .foregroundStyle(.secondary)

            HStack(alignment: .firstTextBaseline) {
                Text(model.mode.title)
                    .font(.system(size: availableWidth < 560 ? 28 : 34, weight: .semibold))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
                Spacer(minLength: 12)
                Text(model.statusText)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .lineLimit(1)
                    .truncationMode(.middle)
            }
        }
        .padding(.horizontal, availableWidth < 620 ? 18 : 28)
        .padding(.top, 24)
        .padding(.bottom, 32)
    }
}

struct DropAreaView: View {
    @ObservedObject var model: AppModel
    @State private var isHovering = false

    var body: some View {
        SettingsGroup {
            VStack(spacing: 12) {
                Image(systemName: model.mode == .images ? "folder" : "doc.badge.plus")
                    .font(.system(size: 48, weight: .regular))
                    .foregroundStyle(active ? AppTheme.blue : AppTheme.secondaryText)
                    .frame(width: 56, height: 56)

                Text(model.mode.importTitle)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(AppTheme.rowText)

                Text(model.mode == .images ? "Drop files or folders here" : "Drop PDF files here")
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(AppTheme.secondaryText)

                Text(model.mode.importSubtitle)
                    .font(.caption)
                    .foregroundStyle(AppTheme.secondaryText)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 420)

                Button("or select files") {
                    model.chooseActiveFiles()
                }
                .buttonStyle(.plain)
                .font(.callout.weight(.medium))
                .foregroundStyle(AppTheme.blue)
                .disabled(model.isRunning)
                .padding(.top, 2)
            }
            .frame(maxWidth: .infinity, minHeight: 210)
            .padding(.horizontal, 22)
            .padding(.vertical, 26)
            .background(
                RoundedRectangle(cornerRadius: 14)
                    .fill(active ? AppTheme.blue.opacity(0.08) : Color.black.opacity(0.025))
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14)
                    .strokeBorder(
                        active ? AppTheme.blue : AppTheme.border,
                        style: StrokeStyle(lineWidth: active ? 1.6 : 1.2, dash: [8, 6])
                    )
            )
            .onHover { hovering in
                isHovering = hovering
            }
        }
        .disabled(model.isRunning)
        .onDrop(of: [.fileURL], isTargeted: $model.isDropTargeted) { providers in
            model.handleDrop(providers)
        }
    }

    private var active: Bool {
        isHovering || model.isDropTargeted
    }
}

struct ImageSettingsView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        SectionBlock(title: "Settings") {
            SettingsRow(icon: "slider.horizontal.3", title: "Quality", subtitle: "\(Int(model.imageQuality)) percent") {
                Slider(value: $model.imageQuality, in: 1...100, step: 1)
                    .frame(minWidth: 120, idealWidth: 180, maxWidth: 220)
            }

            SettingsDivider()

            SettingsRow(icon: "arrow.triangle.2.circlepath", title: "Convert format", subtitle: "Optionally rewrite selected formats") {
                Toggle("", isOn: $model.convertFormat)
                    .labelsHidden()
                    .toggleStyle(.switch)
                    .disabled(model.isRunning)
            }

            if model.convertFormat {
                SettingsDivider()
                SettingsRow(icon: "line.3.horizontal.decrease.circle", title: "Input format", subtitle: "Filter files before processing") {
                    Picker("", selection: $model.inputFormat) {
                        ForEach(ImageFormat.allCases) { format in
                            Text(format.rawValue).tag(format)
                        }
                    }
                    .labelsHidden()
                    .frame(width: 132)
                    .disabled(model.isRunning)
                }

                SettingsDivider()

                SettingsRow(icon: "square.and.arrow.down", title: "Output format", subtitle: "Format for converted files") {
                    Picker("", selection: $model.outputFormat) {
                        ForEach([ImageFormat.webp, .jpg, .png]) { format in
                            Text(format.rawValue).tag(format)
                        }
                    }
                    .labelsHidden()
                    .frame(width: 132)
                    .disabled(model.isRunning)
                }
            }
        }

        ExportGroup(model: model)
    }
}

struct PDFSettingsView: View {
    @ObservedObject var model: AppModel

    var body: some View {
        SectionBlock(title: "Settings") {
            SettingsRow(icon: "doc.text.magnifyingglass", title: "Processing mode", subtitle: model.pdfMode == .optimize ? "Keep text and vector content" : "Render pages into a compact scan-style PDF") {
                Picker("", selection: $model.pdfMode) {
                    ForEach(PdfMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .labelsHidden()
                .frame(width: 160)
                .disabled(model.isRunning)
            }

            if model.pdfMode == .scanDpi {
                SettingsDivider()
                SettingsRow(icon: "gauge.with.dots.needle.bottom.50percent", title: "DPI", subtitle: "\(Int(model.pdfDpi)) DPI") {
                    Slider(value: $model.pdfDpi, in: 30...150, step: 1)
                        .frame(minWidth: 120, idealWidth: 180, maxWidth: 220)
                }
            }
        }

        ExportGroup(model: model)
    }
}

struct ExportGroup: View {
    @ObservedObject var model: AppModel

    var body: some View {
        SectionBlock(title: "Save location") {
            SettingsRow(icon: "tray.and.arrow.down", title: "Save location", subtitle: model.activeOutputFolder.path) {
                Button("Change...") {
                    model.chooseOutputFolder(for: model.mode)
                }
                .textButtonStyle()
                .disabled(model.isRunning)
            }
        }
    }
}

struct SectionBlock<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(AppTheme.rowText)
                .padding(.horizontal, 2)

            SettingsGroup {
                content
            }
        }
    }
}

struct SettingsGroup<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        VStack(spacing: 0) {
            content
        }
        .background(AppTheme.cardBackground, in: RoundedRectangle(cornerRadius: 14))
        .overlay(
            RoundedRectangle(cornerRadius: 14)
                .stroke(AppTheme.border, lineWidth: 1)
        )
    }
}

struct SettingsDivider: View {
    var body: some View {
        Divider()
            .padding(.leading, 56)
    }
}

struct SettingsRow<Trailing: View>: View {
    let icon: String
    let title: String
    let subtitle: String
    @ViewBuilder let trailing: Trailing

    var body: some View {
        ViewThatFits(in: .horizontal) {
            horizontalRow
            verticalRow
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 18)
    }

    private var label: some View {
        HStack(spacing: 14) {
            Image(systemName: icon)
                .font(.system(size: 17, weight: .regular))
                .foregroundStyle(.secondary)
                .frame(width: 24)

            VStack(alignment: .leading, spacing: 3) {
                Text(title)
                    .font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(AppTheme.rowText)
                Text(subtitle)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundStyle(AppTheme.secondaryText)
                    .lineLimit(2)
                    .truncationMode(.middle)
            }
        }
    }

    private var horizontalRow: some View {
        HStack(spacing: 14) {
            label
            Spacer(minLength: 20)
            trailing
        }
    }

    private var verticalRow: some View {
        VStack(alignment: .leading, spacing: 12) {
            label
            trailing
                .padding(.leading, 38)
        }
    }
}

struct ActionFooter: View {
    @ObservedObject var model: AppModel

    var body: some View {
        VStack(spacing: 12) {
            ProgressView(value: model.progress)
                .controlSize(.small)
                .frame(maxWidth: .infinity)

            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 2) {
                    Text(model.isRunning ? "Processing" : "Ready to run")
                        .font(.system(size: 14, weight: .semibold))
                        .foregroundStyle(AppTheme.rowText)
                    Text(model.activeCount == 0 ? "Add files to enable compression" : "\(model.activeCount) items in queue")
                        .font(.caption)
                        .foregroundStyle(AppTheme.secondaryText)
                }

                Spacer()

                Button("Reset") {
                    model.resetActiveQueue()
                }
                .textButtonStyle()
                .disabled(model.isRunning || model.activeCount == 0)

                Button(model.isRunning ? "Running..." : "Run") {
                    model.runActiveJob()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(model.isRunning || model.activeCount == 0)
            }
        }
        .padding(.horizontal, 28)
        .padding(.vertical, 16)
        .background(.regularMaterial)
        .overlay(alignment: .top) {
            Divider()
        }
    }
}

extension View {
    func textButtonStyle() -> some View {
        self
            .buttonStyle(.plain)
            .font(.callout.weight(.medium))
            .foregroundStyle(AppTheme.blue)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(AppTheme.buttonBackground, in: RoundedRectangle(cornerRadius: 8))
    }
}

struct StatusSection: View {
    @ObservedObject var model: AppModel

    var body: some View {
        if model.recentErrors.isEmpty {
            EmptyView()
        } else {
            SettingsGroup {
                ForEach(Array(model.recentErrors.prefix(5).enumerated()), id: \.element.id) { index, error in
                    if index > 0 {
                        SettingsDivider()
                    }
                    SettingsRow(icon: "exclamationmark.triangle", title: error.fileName, subtitle: error.message) {
                        EmptyView()
                    }
                }
            }
        }
    }
}

enum CompressorEngine {
    static func compressImages(
        _ files: [URL],
        outputFolder: URL,
        quality: Double,
        convertFormat: Bool,
        inputFilter: ImageFormat,
        outputFormat: ImageFormat,
        progress: @escaping (Int, Int, URL) -> Void
    ) -> JobResult {
        var result = JobResult()
        var reserved = Set<URL>()
        try? FileManager.default.createDirectory(at: outputFolder, withIntermediateDirectories: true)

        for (index, file) in files.enumerated() {
            defer { progress(index + 1, files.count, file) }
            do {
                if !matches(file, filter: inputFilter) {
                    result.skipped += 1
                    continue
                }
                let targetExtension = convertFormat ? (outputFormat.fileExtension ?? file.pathExtension) : normalizedImageExtension(file.pathExtension)
                let output = uniqueOutputURL(
                    folder: outputFolder,
                    stem: "\(file.deletingPathExtension().lastPathComponent)_compressed",
                    ext: targetExtension,
                    reserved: &reserved
                )
                try writeImage(file, to: output, ext: targetExtension, quality: quality / 100)
                result.processed += 1
            } catch {
                result.errors.append(JobError(fileName: file.lastPathComponent, message: error.localizedDescription))
            }
        }

        return result
    }

    static func compressPDFs(
        _ files: [URL],
        outputFolder: URL,
        mode: PdfMode,
        dpi: Double,
        progress: @escaping (Int, Int, URL) -> Void
    ) -> JobResult {
        var result = JobResult()
        var reserved = Set<URL>()
        try? FileManager.default.createDirectory(at: outputFolder, withIntermediateDirectories: true)

        for (index, file) in files.enumerated() {
            defer { progress(index + 1, files.count, file) }
            do {
                let output = uniqueOutputURL(
                    folder: outputFolder,
                    stem: "\(file.deletingPathExtension().lastPathComponent)_compressed",
                    ext: "pdf",
                    reserved: &reserved
                )
                switch mode {
                case .optimize:
                    try optimizePDF(file, to: output)
                case .scanDpi:
                    try rasterizePDF(file, to: output, dpi: dpi)
                }
                result.processed += 1
            } catch {
                result.errors.append(JobError(fileName: file.lastPathComponent, message: error.localizedDescription))
            }
        }

        return result
    }

    private static func matches(_ file: URL, filter: ImageFormat) -> Bool {
        guard let ext = filter.fileExtension else { return true }
        let current = normalizedImageExtension(file.pathExtension)
        return ext == "jpg" ? current == "jpg" : current == ext
    }

    private static func normalizedImageExtension(_ value: String) -> String {
        let ext = value.lowercased()
        return ext == "jpeg" ? "jpg" : ext
    }

    private static func writeImage(_ source: URL, to output: URL, ext: String, quality: Double) throws {
        guard let imageSource = CGImageSourceCreateWithURL(source as CFURL, nil),
              let cgImage = CGImageSourceCreateImageAtIndex(imageSource, 0, nil) else {
            throw NSError(domain: "VBCompress", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not read image"])
        }

        let type = try imageType(for: ext)
        guard let destination = CGImageDestinationCreateWithURL(output as CFURL, type as CFString, 1, nil) else {
            throw NSError(domain: "VBCompress", code: 2, userInfo: [NSLocalizedDescriptionKey: "Could not create image output"])
        }

        let options: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: max(0.01, min(1.0, quality))
        ]
        CGImageDestinationAddImage(destination, cgImage, options as CFDictionary)
        if !CGImageDestinationFinalize(destination) {
            throw NSError(domain: "VBCompress", code: 3, userInfo: [NSLocalizedDescriptionKey: "Could not write image"])
        }
    }

    private static func imageType(for ext: String) throws -> String {
        switch normalizedImageExtension(ext) {
        case "jpg":
            return UTType.jpeg.identifier
        case "png":
            return UTType.png.identifier
        case "webp":
            return UTType.webP.identifier
        default:
            throw NSError(domain: "VBCompress", code: 4, userInfo: [NSLocalizedDescriptionKey: "Unsupported image format"])
        }
    }

    private static func optimizePDF(_ source: URL, to output: URL) throws {
        guard let document = PDFDocument(url: source) else {
            throw NSError(domain: "VBCompress", code: 5, userInfo: [NSLocalizedDescriptionKey: "Could not read PDF"])
        }
        if !document.write(to: output) {
            throw NSError(domain: "VBCompress", code: 6, userInfo: [NSLocalizedDescriptionKey: "Could not write PDF"])
        }
    }

    private static func rasterizePDF(_ source: URL, to output: URL, dpi: Double) throws {
        guard let document = PDFDocument(url: source), document.pageCount > 0 else {
            throw NSError(domain: "VBCompress", code: 7, userInfo: [NSLocalizedDescriptionKey: "Could not read PDF"])
        }

        guard let consumer = CGDataConsumer(url: output as CFURL) else {
            throw NSError(domain: "VBCompress", code: 8, userInfo: [NSLocalizedDescriptionKey: "Could not create PDF output"])
        }

        var mediaBox = CGRect(origin: .zero, size: CGSize(width: 612, height: 792))
        guard let context = CGContext(consumer: consumer, mediaBox: &mediaBox, nil) else {
            throw NSError(domain: "VBCompress", code: 9, userInfo: [NSLocalizedDescriptionKey: "Could not create PDF context"])
        }

        for pageIndex in 0..<document.pageCount {
            guard let page = document.page(at: pageIndex) else { continue }
            let bounds = page.bounds(for: .mediaBox)
            var pageBox = CGRect(origin: .zero, size: bounds.size)
            context.beginPage(mediaBox: &pageBox)
            context.saveGState()
            context.translateBy(x: 0, y: bounds.height)
            context.scaleBy(x: 1, y: -1)

            if let image = render(page: page, dpi: dpi) {
                context.draw(image, in: CGRect(origin: .zero, size: bounds.size))
            } else {
                page.draw(with: .mediaBox, to: context)
            }

            context.restoreGState()
            context.endPage()
        }
        context.closePDF()
    }

    private static func render(page: PDFPage, dpi: Double) -> CGImage? {
        let bounds = page.bounds(for: .mediaBox)
        let scale = max(0.25, dpi / 72.0)
        let width = Int(bounds.width * scale)
        let height = Int(bounds.height * scale)
        guard let colorSpace = CGColorSpace(name: CGColorSpace.sRGB),
              let context = CGContext(
                  data: nil,
                  width: width,
                  height: height,
                  bitsPerComponent: 8,
                  bytesPerRow: 0,
                  space: colorSpace,
                  bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue
              ) else {
            return nil
        }
        context.setFillColor(NSColor.white.cgColor)
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        context.scaleBy(x: scale, y: scale)
        page.draw(with: .mediaBox, to: context)
        return context.makeImage()
    }

    private static func uniqueOutputURL(folder: URL, stem: String, ext: String, reserved: inout Set<URL>) -> URL {
        var candidate = folder.appendingPathComponent(stem).appendingPathExtension(ext)
        var index = 2
        while FileManager.default.fileExists(atPath: candidate.path) || reserved.contains(candidate) {
            candidate = folder.appendingPathComponent("\(stem)_\(index)").appendingPathExtension(ext)
            index += 1
        }
        reserved.insert(candidate)
        return candidate
    }
}

#if !E2E_TEST
@main
struct VBCompressSwiftApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 820, minHeight: 620)
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
    }
}
#endif
