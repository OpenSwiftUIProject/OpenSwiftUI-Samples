package org.openswiftui.samples

import android.content.pm.ApplicationInfo
import android.os.Bundle
import android.system.Os
import android.system.OsConstants
import com.flowkey.uikit.UIKitActivity

class MainActivity : UIKitActivity() {
    private external fun configureOpenSwiftUI()

    override fun onCreate(savedInstanceState: Bundle?) {
        System.loadLibrary(getString(R.string.native_lib_name))
        if (applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE != 0 &&
            intent.getBooleanExtra("printTree", false)) {
            Os.setenv("OPENSWIFTUI_PRINT_TREE", "1", true)
            val output = Os.open(
                "${filesDir.absolutePath}/display-list.log",
                OsConstants.O_WRONLY or OsConstants.O_CREAT or OsConstants.O_TRUNC,
                384
            )
            Os.dup2(output, OsConstants.STDOUT_FILENO)
            Os.dup2(output, OsConstants.STDERR_FILENO)
            Os.close(output)
        }
        configureOpenSwiftUI()
        super.onCreate(savedInstanceState)
    }
}
