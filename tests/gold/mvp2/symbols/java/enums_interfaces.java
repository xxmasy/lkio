package com.example.crm;

import java.io.Closeable;

/**
 * Enums, Interfaces, Records, and Nested Types Gold Fixture.
 */
public enum OrderStatus {

    INIT(0, "初始化"),
    PAID(1, "已支付"),
    RUNNING {
        @Override
        public String label() {
            return "running";
        }
    };

    private final int code;
    private final String desc;

    OrderStatus() {
        this(0, "default");
    }

    OrderStatus(int code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public String label() {
        return desc;
    }
}

public record OrderRecord(String id, Long amount) {
    public OrderRecord {
        if (amount < 0) {
            throw new IllegalArgumentException("Amount cannot be negative");
        }
    }
}

public interface OrderApi<T> extends Closeable {

    String API_VERSION = "v1.0";

    T findOrder(String id);

    default boolean isActive() {
        return true;
    }

    static void printVersion() {
        // static method
    }
}

public class OrderContainer {

    public static class Builder {
        private String orderId;

        public Builder orderId(String orderId) {
            this.orderId = orderId;
            return this;
        }
    }
}
