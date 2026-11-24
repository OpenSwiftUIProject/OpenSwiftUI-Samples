#if os(Android)
import Game2048
import OpenSwiftUI
import OpenSwiftUIAndroidDemo

@_cdecl("Java_org_openswiftui_samples_MainActivity_configureOpenSwiftUI")
public func configureOpenSwiftUI(
    _ environment: UnsafeMutableRawPointer?,
    _ activity: UnsafeMutableRawPointer?
) {
    AndroidUIKitDemoRunner.configure(
        app: Game.self,
        javaEnvironment: environment
    )
}
#endif
