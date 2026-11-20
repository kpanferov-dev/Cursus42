//go:build linux || darwin

package main

import (
	"os"
	"os/signal"
	"syscall"
	"unsafe"
)

// termSize returns the terminal size of stdout; ok is false when stdout is
// not a terminal (pipe, file, IDE console...).
func termSize() (rows, cols int, ok bool) {
	var ws struct{ Row, Col, XPixel, YPixel uint16 }
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, os.Stdout.Fd(), uintptr(syscall.TIOCGWINSZ), uintptr(unsafe.Pointer(&ws)))
	if errno != 0 || ws.Row == 0 || ws.Col == 0 {
		return 0, 0, false
	}
	return int(ws.Row), int(ws.Col), true
}

// notifyResize delivers terminal resize signals to c.
func notifyResize(signals chan<- os.Signal) { signal.Notify(signals, syscall.SIGWINCH) }
