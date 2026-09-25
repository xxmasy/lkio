package com.example.crm;

import java.util.List;

/**
 * Overload and Receiver Parameter Gold Fixture for Java Symbol Extraction.
 */
public class OverloadService {

    private String config;
    private int retries;

    // Constructor Overloading (3 levels)
    public OverloadService() {
        this("default", 3);
    }

    public OverloadService(String config) {
        this(config, 3);
    }

    public OverloadService(String config, int retries) {
        this.config = config;
        this.retries = retries;
    }

    // Method Overloading (5 levels)
    public void process() {
        process("default");
    }

    public void process(String data) {
        process(data, 1);
    }

    public void process(String data, int priority) {
        // process with priority
    }

    public void process(List<String> dataList) {
        // batch process
    }

    public void process(String... varargs) {
        // varargs process
    }

    // Method with Receiver Parameter (LOCK-JAVA-02)
    public void inspect(OverloadService this, String target) {
        // receiver parameter 'OverloadService this' must NOT enter canonical overload signature
    }
}
