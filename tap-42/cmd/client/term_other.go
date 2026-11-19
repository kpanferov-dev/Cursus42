//go:build !linux && !darwin

package main

import "os"

// On other platforms the pinned map is disabled; the CLI prints the map inline.
func termSize() (rows, cols int, ok bool) { return 0, 0, false }

func notifyResize(c chan<- os.Signal) {}
