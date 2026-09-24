<template>
  <div class="user-profile">
    <h2>User Profile</h2>
  </div>
</template>

<script>
export default {
  name: 'UserProfile',
  data() {
    return {
      name: 'John'
    }
  },
  methods: {
    loadUser() {
      console.log('Loading user')
    }
  }
}
</script>

<style>
.user-profile { margin: 10px; }
</style>
