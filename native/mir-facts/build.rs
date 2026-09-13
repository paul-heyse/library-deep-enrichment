//! Bind execution to the same sysroot as the compiler-private build.
fn main() {
    let rustc = std::env::var_os("RUSTC").expect("Cargo supplies RUSTC");
    let version = std::process::Command::new(&rustc)
        .arg("-vV")
        .output()
        .expect("compiler version");
    let version = String::from_utf8(version.stdout).expect("compiler identity");
    assert!(
        version.contains("8fa1c96cfd489e4c27654c144ae871ce2c4db6c6"),
        "MIR adapter requires the reviewed compiler commit"
    );
    let output = std::process::Command::new(rustc)
        .args(["--print", "sysroot"])
        .output()
        .expect("query build sysroot");
    assert!(output.status.success());
    let sysroot = String::from_utf8(output.stdout).expect("UTF-8 sysroot");
    println!("cargo:rustc-link-arg=-Wl,-rpath,{}/lib", sysroot.trim());
    println!(
        "cargo:rustc-env=LIBRARY_GUIDES_BUILD_SYSROOT={}",
        sysroot.trim()
    );
}
