#if os(Android)
import HelloWorld
import OpenSwiftUI
import OpenSwiftUIAndroidDemo

@_cdecl("Java_org_openswiftui_samples_MainActivity_configureOpenSwiftUI")
public func configureOpenSwiftUI(
    _ environment: UnsafeMutableRawPointer?,
    _ activity: UnsafeMutableRawPointer?
) {
    AndroidUIKitDemoRunner.configure(
        app: HelloWorld.self,
        javaEnvironment: environment
    )
}
#endif
