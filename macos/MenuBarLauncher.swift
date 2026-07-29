import AppKit
import CoreImage
import Foundation

private enum LauncherError: LocalizedError {
    case invalidProjectFolder
    case pairingUnavailable

    var errorDescription: String? {
        switch self {
        case .invalidProjectFolder:
            return "Choose the VLC Remote project folder (the one containing Makefile)."
        case .pairingUnavailable:
            return "The remote started, but its pairing QR could not be created. See the service log."
        }
    }
}

@main
final class MenuBarLauncher: NSObject, NSApplicationDelegate {
    private let statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    private let defaultsKey = "projectRoot"
    private let statusMenuItem = NSMenuItem(title: "Remote is stopped", action: nil, keyEquivalent: "")
    private let startMenuItem = NSMenuItem(title: "Start Remote", action: #selector(startRemote), keyEquivalent: "s")
    private let showQRMenuItem = NSMenuItem(title: "Show Pairing QR", action: #selector(showPairingQR), keyEquivalent: "q")
    private let stopMenuItem = NSMenuItem(title: "Stop Phone Remote", action: #selector(stopRemote), keyEquivalent: ".")
    private var serviceProcess: Process?
    private var pairingURL: String?
    private var qrWindow: NSWindow?
    private var isStarting = false
    private var startsAfterProjectSelection = false

    static func main() {
        let application = NSApplication.shared
        let delegate = MenuBarLauncher()
        application.delegate = delegate
        application.setActivationPolicy(.regular)
        application.run()
    }

    func applicationDidFinishLaunching(_ notification: Notification) {
        configureMenu()
        if projectRoot == nil {
            startsAfterProjectSelection = true
            chooseProjectFolder(nil)
        } else {
            startRemote()
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        stopRemote()
    }

    func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
        if pairingURL != nil {
            showPairingQR()
        } else if serviceProcess?.isRunning != true {
            startRemote()
        }
        return true
    }

    private var projectRoot: URL? {
        guard let rawPath = UserDefaults.standard.string(forKey: defaultsKey) else { return nil }
        let folder = URL(fileURLWithPath: rawPath, isDirectory: true).standardizedFileURL
        return isProjectRoot(folder) ? folder : nil
    }

    private func isProjectRoot(_ folder: URL) -> Bool {
        let requiredPaths = [
            "Makefile",
            ".venv/bin/python",
            "scripts/run_menu_bar_service.py",
            "scripts/show_pairing_qr.py"
        ]
        return requiredPaths.allSatisfy {
            FileManager.default.fileExists(atPath: folder.appendingPathComponent($0).path)
        }
    }

    private func configureMenu() {
        guard let button = statusItem.button else { return }
        button.image = NSImage(systemSymbolName: "dot.radiowaves.left.and.right", accessibilityDescription: "VLC Remote")
        button.image?.isTemplate = true

        let menu = NSMenu()
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)
        menu.addItem(.separator())
        for item in [startMenuItem, showQRMenuItem, stopMenuItem] {
            item.target = self
            menu.addItem(item)
        }
        menu.addItem(.separator())
        let chooseItem = NSMenuItem(title: "Choose Project Folder…", action: #selector(chooseProjectFolder), keyEquivalent: "")
        chooseItem.target = self
        menu.addItem(chooseItem)
        let logItem = NSMenuItem(title: "Show Service Log", action: #selector(showServiceLog), keyEquivalent: "")
        logItem.target = self
        menu.addItem(logItem)
        menu.addItem(.separator())
        let quitItem = NSMenuItem(title: "Quit VLC Remote", action: #selector(quit), keyEquivalent: "q")
        quitItem.target = self
        menu.addItem(quitItem)
        statusItem.menu = menu
        updateMenuState()
    }

    private func updateMenuState() {
        let running = serviceProcess?.isRunning == true
        let status = isStarting ? "Starting remote…" : (running ? "Remote is running on this Mac" : "Remote is stopped")
        statusMenuItem.title = status
        startMenuItem.isEnabled = !running && !isStarting && projectRoot != nil
        showQRMenuItem.isEnabled = running && pairingURL != nil
        stopMenuItem.isEnabled = running
    }

    @objc private func chooseProjectFolder(_ sender: Any?) {
        NSApp.activate(ignoringOtherApps: true)
        let panel = NSOpenPanel()
        panel.title = "Choose the VLC Remote project folder"
        panel.message = "Choose the folder containing Makefile and the .venv directory."
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let folder = panel.url {
            guard isProjectRoot(folder) else {
                present(error: LauncherError.invalidProjectFolder)
                return
            }
            UserDefaults.standard.set(folder.standardizedFileURL.path, forKey: defaultsKey)
            updateMenuState()
            if startsAfterProjectSelection {
                startsAfterProjectSelection = false
                startRemote()
            }
        }
    }

    @objc private func startRemote() {
        guard let root = projectRoot else {
            chooseProjectFolder(nil)
            return
        }
        do {
            let logHandle = try openLogFile()
            let process = Process()
            process.executableURL = root.appendingPathComponent(".venv/bin/python")
            process.arguments = ["scripts/run_menu_bar_service.py"]
            process.currentDirectoryURL = root
            process.standardOutput = logHandle
            process.standardError = logHandle
            process.terminationHandler = { [weak self] _ in
                DispatchQueue.main.async {
                    self?.serviceProcess = nil
                    self?.pairingURL = nil
                    self?.isStarting = false
                    self?.qrWindow?.close()
                    self?.updateMenuState()
                }
            }
            try process.run()
            serviceProcess = process
            isStarting = true
            updateMenuState()
            waitForServiceReady(from: root, attemptsRemaining: 40)
        } catch {
            stopRemote()
            present(error: error)
        }
    }

    @objc private func stopRemote() {
        qrWindow?.close()
        pairingURL = nil
        isStarting = false
        if let process = serviceProcess, process.isRunning {
            process.terminate()
        }
        serviceProcess = nil
        updateMenuState()
    }

    @objc private func showPairingQR() {
        guard let url = pairingURL else { return }
        qrWindow?.close()
        let imageView = NSImageView(image: qrImage(for: url))
        imageView.translatesAutoresizingMaskIntoConstraints = false
        imageView.imageScaling = .scaleProportionallyUpOrDown

        let explanation = NSTextField(wrappingLabelWithString: "Scan this QR code with a phone on the same home Wi-Fi. The pairing link is treated like a password.")
        explanation.translatesAutoresizingMaskIntoConstraints = false
        explanation.alignment = .center
        explanation.maximumNumberOfLines = 3

        let copyButton = NSButton(title: "Copy Pairing Link", target: self, action: #selector(copyPairingLink))
        copyButton.translatesAutoresizingMaskIntoConstraints = false
        let stack = NSStackView(views: [imageView, explanation, copyButton])
        stack.orientation = .vertical
        stack.alignment = .centerX
        stack.spacing = 16
        stack.edgeInsets = NSEdgeInsets(top: 24, left: 24, bottom: 24, right: 24)

        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 390, height: 500), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.title = "Pair VLC Remote"
        window.contentView = stack
        window.center()
        window.isReleasedWhenClosed = false
        qrWindow = window
        NSApp.activate(ignoringOtherApps: true)
        window.makeKeyAndOrderFront(nil)
    }

    @objc private func copyPairingLink() {
        guard let pairingURL else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(pairingURL, forType: .string)
    }

    @objc private func showServiceLog() {
        NSWorkspace.shared.activateFileViewerSelecting([logFileURL()])
    }

    @objc private func quit() {
        NSApp.terminate(nil)
    }

    private func capturePairingURL(from root: URL) throws -> String {
        let process = Process()
        let output = Pipe()
        process.executableURL = root.appendingPathComponent(".venv/bin/python")
        process.arguments = ["scripts/show_pairing_qr.py", "--print-primary-url", "--port", "8000"]
        process.currentDirectoryURL = root
        process.standardOutput = output
        process.standardError = FileHandle.nullDevice
        try process.run()
        process.waitUntilExit()
        let data = output.fileHandleForReading.readDataToEndOfFile()
        guard process.terminationStatus == 0,
              let url = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
              url.hasPrefix("http://"), url.contains("#token=") else {
            throw LauncherError.pairingUnavailable
        }
        return url
    }

    private func waitForServiceReady(from root: URL, attemptsRemaining: Int) {
        guard let process = serviceProcess, process.isRunning else {
            isStarting = false
            updateMenuState()
            present(error: LauncherError.pairingUnavailable)
            return
        }
        let healthURL = URL(string: "http://127.0.0.1:8000/api/v1/health")!
        URLSession.shared.dataTask(with: healthURL) { [weak self] _, response, _ in
            DispatchQueue.main.async {
                guard let self else { return }
                if let http = response as? HTTPURLResponse, http.statusCode == 200 {
                    do {
                        self.pairingURL = try self.capturePairingURL(from: root)
                        self.isStarting = false
                        self.updateMenuState()
                        self.showPairingQR()
                    } catch {
                        self.stopRemote()
                        self.present(error: error)
                    }
                } else if attemptsRemaining > 1, self.serviceProcess?.isRunning == true {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
                        self.waitForServiceReady(from: root, attemptsRemaining: attemptsRemaining - 1)
                    }
                } else {
                    self.stopRemote()
                    self.present(error: LauncherError.pairingUnavailable)
                }
            }
        }.resume()
    }

    private func qrImage(for value: String) -> NSImage {
        let filter = CIFilter(name: "CIQRCodeGenerator")!
        filter.setValue(Data(value.utf8), forKey: "inputMessage")
        filter.setValue("M", forKey: "inputCorrectionLevel")
        let scaled = filter.outputImage?.transformed(by: CGAffineTransform(scaleX: 8, y: 8)) ?? CIImage()
        let representation = NSCIImageRep(ciImage: scaled)
        let image = NSImage(size: scaled.extent.size)
        image.addRepresentation(representation)
        return image
    }

    private func logFileURL() -> URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Logs/MacVlcRemote/menu-bar-service.log")
    }

    private func openLogFile() throws -> FileHandle {
        let directory = logFileURL().deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true, attributes: [.posixPermissions: 0o700])
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: directory.path)
        let file = logFileURL()
        if !FileManager.default.fileExists(atPath: file.path) {
            FileManager.default.createFile(atPath: file.path, contents: nil, attributes: [.posixPermissions: 0o600])
        }
        try FileManager.default.setAttributes([.posixPermissions: 0o600], ofItemAtPath: file.path)
        let handle = try FileHandle(forWritingTo: file)
        try handle.seekToEnd()
        return handle
    }

    private func present(error: Error) {
        NSAlert(error: error).runModal()
    }
}
