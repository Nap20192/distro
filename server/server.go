package main

import (
        "encoding/json"
        "fmt"
        "log"
        "net"
        "time"
)

type Request struct {
        RequestID string                 `json:"request_id"`
        Method    string                 `json:"method"`
        Params    map[string]interface{} `json:"params"`
}

type Response struct {
        RequestID string      `json:"request_id"`
        Result    interface{} `json:"result,omitempty"`
        Error     string      `json:"error,omitempty"`
}

func handleRequest(req Request) Response {
        switch req.Method {

        case "add":
                a := int(req.Params["a"].(float64))
                b := int(req.Params["b"].(float64))
                return Response{RequestID: req.RequestID, Result: a + b}

        case "get_time":
                return Response{
                        RequestID: req.RequestID,
                        Result:    time.Now().Format(time.RFC3339),
                }

        case "reverse_string":
                s := req.Params["s"].(string)
                r := []rune(s)
                for i, j := 0, len(r)-1; i < j; i, j = i+1, j-1 {
                        r[i], r[j] = r[j], r[i]
                }
                return Response{RequestID: req.RequestID, Result: string(r)}

        default:
                return Response{RequestID: req.RequestID, Error: "unknown method"}
        }
}

func main() {
        listener, err := net.Listen("tcp", ":5000")

        if err != nil {
                log.Fatal(err)
        }

        fmt.Println("RPC Server listening on port 5000")

        for {
                conn, err := listener.Accept()
                if err != nil {
                        continue
                }

                go func(c net.Conn) {
                        defer c.Close()

                        decoder := json.NewDecoder(c)
                        encoder := json.NewEncoder(c)

                        var req Request
                        if err := decoder.Decode(&req); err != nil {
                                return
                        }

                        time.Sleep(2 * time.Second)
                        resp := handleRequest(req)
                        encoder.Encode(resp)

                }(conn)
        }
}
