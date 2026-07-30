#!/usr/bin/env swift
// Freisteller: natives Subject-Lifting ueber das Vision-Framework (macOS 14+).
// Muster uebernommen aus raycast/extensions, remove-background-powered-by-mac (MIT).
// Aufruf: swift freisteller.swift <eingabe.jpg> <ausgabe.png>

import CoreImage
import Foundation
import Vision

func fehler(_ text: String) -> Never {
    FileHandle.standardError.write(Data(("FEHLER: " + text + "\n").utf8))
    exit(1)
}

guard CommandLine.arguments.count == 3 else {
    fehler("Aufruf: freisteller.swift <eingabe.jpg> <ausgabe.png>")
}
let eingabe = URL(fileURLWithPath: CommandLine.arguments[1])
let ausgabe = URL(fileURLWithPath: CommandLine.arguments[2])

guard let bild = CIImage(contentsOf: eingabe) else {
    fehler("Bild nicht lesbar: \(eingabe.path)")
}

let request = VNGenerateForegroundInstanceMaskRequest()
let handler = VNImageRequestHandler(ciImage: bild, options: [:])
do { try handler.perform([request]) } catch { fehler("Vision: \(error.localizedDescription)") }

guard let ergebnis = request.results?.first, !ergebnis.allInstances.isEmpty else {
    fehler("kein Vordergrund-Motiv erkannt in \(eingabe.lastPathComponent)")
}

do {
    let puffer = try ergebnis.generateMaskedImage(
        ofInstances: ergebnis.allInstances, from: handler,
        croppedToInstancesExtent: true)
    let freigestellt = CIImage(cvImageBuffer: puffer)
    let kontext = CIContext()
    try kontext.writePNGRepresentation(
        of: freigestellt, to: ausgabe,
        format: .RGBA8, colorSpace: CGColorSpaceCreateDeviceRGB())
    let groesse = freigestellt.extent
    print("OK — \(ergebnis.allInstances.count) Instanz(en), \(Int(groesse.width))×\(Int(groesse.height)) px → \(ausgabe.path)")
} catch {
    fehler("Maskierung/Export: \(error.localizedDescription)")
}
