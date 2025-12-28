package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"os"
	"time"

	"github.com/google/uuid"
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

/* ---------- helpers ---------- */

func prettyPrintJSON(v interface{}) {
	data, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		fmt.Println("JSON marshal error:", err)
		return
	}
	fmt.Println(string(data))
}

/* ---------- RPC ---------- */

func callRPC(serverAddr string, req Request) (*Response, error) {
	conn, err := net.DialTimeout("tcp", serverAddr, 2*time.Second)
	if err != nil {
		return nil, err
	}
	defer conn.Close()

	conn.SetDeadline(time.Now().Add(2 * time.Second))

	encoder := json.NewEncoder(conn)
	decoder := json.NewDecoder(conn)

	if err := encoder.Encode(req); err != nil {
		return nil, err
	}

	var resp Response
	if err := decoder.Decode(&resp); err != nil {
		return nil, err
	}

	return &resp, nil
}

func main() {
	serverAddr := "18.212.213.203:5000"

	if len(os.Args) < 2 {
		fmt.Println("Usage:")
		fmt.Println("  add --a 10 --b 20")
		fmt.Println("  get_time")
		fmt.Println("  reverse_string --s hello")
		os.Exit(1)
	}

	command := os.Args[1]

	var req Request
	req.RequestID = uuid.New().String()
	req.Params = make(map[string]interface{})

	switch command {

	case "add":
		addCmd := flag.NewFlagSet("add", flag.ExitOnError)
		a := addCmd.Int("a", 0, "first number")
		b := addCmd.Int("b", 0, "second number")
		addCmd.Parse(os.Args[2:])

		req.Method = "add"
		req.Params["a"] = *a
		req.Params["b"] = *b

	case "get_time":
		req.Method = "get_time"

	case "reverse_string":
		revCmd := flag.NewFlagSet("reverse_string", flag.ExitOnError)
		s := revCmd.String("s", "", "string to reverse")
		revCmd.Parse(os.Args[2:])

		if *s == "" {
			fmt.Println("reverse_string requires --s")
			os.Exit(1)
		}

		req.Method = "reverse_string"
		req.Params["s"] = *s

	default:
		fmt.Println("Unknown command:", command)
		os.Exit(1)
	}

	maxRetries := 3
	for i := 1; i <= maxRetries; i++ {
		fmt.Println("Attempt", i)

		resp, err := callRPC(serverAddr, req)
		if err != nil {
			fmt.Println("Error:", err)
			continue
		}

		if resp.RequestID != "" && resp.RequestID != req.RequestID {
			fmt.Printf("Warning: response request_id mismatch (got=%s want=%s)\n", resp.RequestID, req.RequestID)
		}

		fmt.Println("Response:")
		prettyPrintJSON(resp)

		if resp.Error != "" {
			fmt.Println("RPC Error:", resp.Error)
			return
		}

		fmt.Println("Result:", resp.Result)
		return
	}

	fmt.Println("RPC failed after retries")
}
