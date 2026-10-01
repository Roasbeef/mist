//// A raw HTTP peer observes parser refusal before any application callback.

import gleam/bytes_tree
import gleam/erlang/process
import gleam/http/response
import gleam/io
import logging
import mist

/// Starts a loopback listener whose stdout records every admitted request.
///
/// ## Examples
///
/// `start(8000)` reports READY after the listener owns its socket.
pub fn start(port: Int) {
  logging.configure()
  logging.set_level(logging.Emergency)
  let assert Ok(_) =
    mist.new(fn(_) {
      io.println("HANDLED")
      response.new(200) |> response.set_body(mist.Bytes(bytes_tree.new()))
    })
    |> mist.bind("127.0.0.1")
    |> mist.port(port)
    |> mist.start
  io.println("READY")
  process.sleep_forever()
}
