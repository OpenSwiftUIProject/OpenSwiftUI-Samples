#if OpenSwiftUI
import OpenSwiftUI
#else
import SwiftUI
#endif

public struct HelloWorld: App {
    public init() {}

    public var body: some Scene {
        WindowGroup {
            ContentView()
        }
    }
}
